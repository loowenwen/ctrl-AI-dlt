import os
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import LabelEncoder
from dotenv import load_dotenv
import boto3
from botocore.config import Config
from strands import Agent, tool
from strands.handlers.callback_handler import PrintingCallbackHandler
from strands.models.bedrock import BedrockModel

# load environment variables
load_dotenv()

# AWS configuration
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_SESSION_TOKEN = os.getenv("AWS_SESSION_TOKEN")

AWS_REGION = "us-east-1"
BEDROCK_MODEL_ID = (
    "arn:aws:bedrock:us-east-1:371061166839:inference-profile/us.anthropic.claude-3-5-sonnet-20240620-v1:0"
)

# logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@dataclass
class PriceEstimate:
    """enhanced result structure for price estimates"""
    flat_type: str
    project_location: str
    project_tier: str
    exercise_date: str
    estimated_price: Optional[float]
    confidence_interval: Tuple[Optional[float], Optional[float]]
    sample_size: int
    historical_trend: Optional[str]
    methodology: str


class BTOProjectClassifier:
    """classify BTO projects into Standard/Plus/Prime tiers"""
    
    def __init__(self):
        self.session = boto3.Session(
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            aws_session_token=AWS_SESSION_TOKEN,
            region_name=AWS_REGION,
        )
        
        self.model = BedrockModel(
            model_id=BEDROCK_MODEL_ID,
            max_tokens=64,
            temperature=0,
            boto_client_config=Config(
                read_timeout=120,
                connect_timeout=120,
                retries=dict(max_attempts=3, mode="adaptive"),
            ),
            boto_session=self.session,
        )
        
        self.agent = Agent(
            model=self.model,
            system_prompt="""
            You are an HDB BTO project classifier for Singapore. 
            
            Classification Rules:
            - Prime: Central locations (Queenstown, Kallang/Whampoa, Bukit Merah, Toa Payoh Central), 
                     near CBD, restricted eligibility, highest prices
            - Plus: Mature towns near MRT, good connectivity (Ang Mo Kio, Bedok, Clementi, Jurong East),
                    attractive locations with good amenities
            - Standard: Non-mature estates, further from city center, basic amenities
            
            Always classify into exactly one category: Standard, Plus, or Prime.
            Return only the classification without explanation.
            """,
            callback_handler=PrintingCallbackHandler(),
        )
    
    def classify(self, project_town: str, project_name: Optional[str] = None) -> str:
        """classify a BTO project into tier"""
        prompt = f"Town/Estate: {project_town}\n"
        if project_name:
            prompt += f"Project Name: {project_name}\n"
        prompt += "\nClassify this HDB BTO project as: Standard, Plus, or Prime"
        
        result = str(self.agent(prompt)).strip()
        
        # normalize output
        result_lower = result.lower()
        if "prime" in result_lower:
            return "Prime"
        elif "plus" in result_lower:
            return "Plus"
        else:
            return "Standard"


class EnhancedBTOCostEstimator:
    """enhanced BTO cost estimator using classification and regression"""
    
    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.df = self._load_and_prepare_data(csv_path)
        self.classifier = BTOProjectClassifier()
        logger.info(f"Loaded {len(self.df)} records from {csv_path}")
    
    def _load_and_prepare_data(self, path: str) -> pd.DataFrame:
        """load and prepare the BTO pricing data"""
        df = pd.read_csv(path)
        
        # normalize column names
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
        
        # standardize column names
        column_mapping = {
            'town': 'project_location',
            'estate': 'project_location', 
            'location': 'project_location',
            'type': 'flat_type',
            'room_type': 'flat_type',
            'price': 'median_price',
            'avg_price': 'median_price',
            'launch_date': 'date',
            'application_date': 'date',
            'sales_launch': 'date',
            'exercise_date': 'date',
            'exercise': 'date',
            'project_type': 'project_tier'
        }
        
        for old_col, new_col in column_mapping.items():
            if old_col in df.columns and new_col not in df.columns:
                df[new_col] = df[old_col]
        
        # normalize project tier using project_type if available
        if 'project_tier' in df.columns:
            df['project_tier'] = df['project_tier'].astype(str).str.strip().str.lower()
            tier_map = {
                'standard projects': 'Standard',
                'plus project': 'Plus',
                'prime project': 'Prime',
            }
            df['project_tier'] = df['project_tier'].map(lambda x: tier_map.get(x, x.title()))

        # parse dates (prefer exercise_date/exercise if present -> mapped to 'date')
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            df['date_ordinal'] = df['date'].map(lambda x: x.toordinal() if pd.notna(x) else None)
        else:
            # Ensure the column exists to avoid downstream KeyErrors
            if 'date_ordinal' not in df.columns:
                df['date_ordinal'] = np.nan
        
        # ensure required columns exist
        required_cols = ['project_location', 'flat_type', 'median_price']
        for col in required_cols:
            if col not in df.columns:
                df[col] = None
        
        # convert price columns to numeric
        price_cols = ['min_price', 'median_price', 'max_price']
        for col in price_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # normalize text fields
        if 'project_location' in df.columns:
            df['project_location'] = df['project_location'].astype(str).str.strip().str.lower()
        if 'flat_type' in df.columns:
            df['flat_type'] = df['flat_type'].astype(str).str.strip().str.lower()
            # canonicalize variations like "2-room flexi" -> "2-room"
            df['flat_type'] = df['flat_type'].str.replace(r'(\d+-room).*', r'\1', regex=True)
        
        # add project tier if not present (classify existing data)
        if 'project_tier' not in df.columns:
            logger.info("Project tier not found in data. Will classify on-demand.")
        
        return df
    
    def _filter_data(self, flat_type: str, project_tier: str) -> pd.DataFrame:
        """filter data by flat type and project tier"""
        filtered_df = self.df.copy()
        
        # filter by flat type
        if flat_type:
            flat_type_normalized = flat_type.lower().strip()
            filtered_df = filtered_df[
                filtered_df['flat_type'].str.contains(flat_type_normalized, na=False)
            ]
        
        # filter by project tier
        if 'project_tier' in filtered_df.columns:
            filtered_df = filtered_df[
                filtered_df['project_tier'].str.lower() == project_tier.lower()
            ]
        else:
            # If no tier column, we need to classify each location
            # This is computationally expensive, so we'll sample or use heuristics
            logger.warning("No project_tier column found. Using heuristic filtering.")
            # Add basic heuristic filtering based on known tier locations
            tier_keywords = {
                'prime': ['queenstown', 'kallang', 'bukit merah', 'toa payoh'],
                'plus': ['ang mo kio', 'bedok', 'clementi', 'jurong east', 'tampines'],
                'standard': []  # Default case
            }
            
            if project_tier.lower() in ['prime', 'plus']:
                keywords = tier_keywords[project_tier.lower()]
                if keywords:
                    mask = filtered_df['project_location'].str.contains(
                        '|'.join(keywords), na=False, case=False
                    )
                    filtered_df = filtered_df[mask]
        
        return filtered_df
    
    def _perform_regression(self, data: pd.DataFrame, target_date_ordinal: int) -> Dict:
        """Perform regression analysis on filtered data"""
        if len(data) < 3:
            return {
                'predicted_price': None,
                'confidence_interval': (None, None),
                'trend': 'insufficient_data',
                'methodology': 'insufficient_data'
            }
        
        # prepare regression data
        if 'date_ordinal' not in data.columns:
            # If no temporal signal, fallback to statistics
            mean_price = data['median_price'].mean()
            std_price = data['median_price'].std()
            return {
                'predicted_price': mean_price,
                'confidence_interval': (mean_price - std_price, mean_price + std_price),
                'trend': 'statistical_average',
                'methodology': 'mean_with_std_no_date'
            }

        valid_data = data.dropna(subset=['date_ordinal', 'median_price'])
        
        if len(valid_data) < 3:
            # fallback to simple statistics
            mean_price = data['median_price'].mean()
            std_price = data['median_price'].std()
            return {
                'predicted_price': mean_price,
                'confidence_interval': (mean_price - std_price, mean_price + std_price),
                'trend': 'statistical_average',
                'methodology': 'mean_with_std'
            }
        
        # perform linear regression
        X = valid_data['date_ordinal'].values.reshape(-1, 1)
        y = valid_data['median_price'].values
        
        model = LinearRegression()
        model.fit(X, y)
        
        # predict for target date
        predicted_price = model.predict([[target_date_ordinal]])[0]
        
        # calculate confidence interval (simple approach)
        residuals = y - model.predict(X)
        mse = np.mean(residuals**2)
        std_error = np.sqrt(mse)
        
        confidence_interval = (
            predicted_price - 1.96 * std_error,  # 95% CI
            predicted_price + 1.96 * std_error
        )
    
        # determine trend
        slope = model.coef_[0]
        if slope > 1000:  # SGD per year
            trend = 'increasing'
        elif slope < -1000:
            trend = 'decreasing'
        else:
            trend = 'stable'
        
        return {
            'predicted_price': predicted_price,
            'confidence_interval': confidence_interval,
            'trend': trend,
            'methodology': 'linear_regression'
        }
    
    def estimate_cost(
        self,
        project_location: str,
        flat_type: str,
        exercise_date: str = "2025-10-01",
        project_name: Optional[str] = None,
        use_existing_classification: bool = True
        ) -> PriceEstimate:
        """estimate BTO cost using classification and regression pipeline"""
    
        logger.info(f"Estimating cost for {flat_type} in {project_location}")
        
        # step 1: classify the project
        if use_existing_classification and 'project_tier' in self.df.columns:
            location_matches = self.df[
                self.df['project_location'].str.contains(project_location.lower(), na=False)
            ]
            if len(location_matches) > 0:
                project_tier = location_matches['project_tier'].iloc[0]
                logger.info(f"Found existing classification: {project_tier}")
            else:
                project_tier = self.classifier.classify(project_location, project_name)
                logger.info(f"Agent classified as: {project_tier}")
        else:
            project_tier = self.classifier.classify(project_location, project_name)
            logger.info(f"Agent classified as: {project_tier}")
        
        # step 2: parse exercise date
        exercise_dt = datetime.strptime(exercise_date, "%Y-%m-%d")
        target_ordinal = exercise_dt.toordinal()
        
        # step 3: filter historical data
        filtered_data = self._filter_data(flat_type, project_tier)
        logger.info(f"Found {len(filtered_data)} matching records for {flat_type} / {project_tier}")
        
        # fallback logic
        if filtered_data.empty:
            logger.warning("No matching records found. Falling back to flat_type only.")
            filtered_data = self.df[self.df['flat_type'].str.contains(flat_type.lower(), na=False)]
        
        if filtered_data.empty:
            logger.warning("Still no matches. Falling back to ALL data.")
            filtered_data = self.df.copy()
        
        # step 4: perform regression analysis
        regression_results = self._perform_regression(filtered_data, target_ordinal)
        
        # step 5: create result
        estimate = PriceEstimate(
            flat_type=flat_type,
            project_location=project_location,
            project_tier=project_tier,
            exercise_date=exercise_date,
            estimated_price=regression_results['predicted_price'],
            confidence_interval=regression_results['confidence_interval'],
            sample_size=len(filtered_data),
            historical_trend=regression_results['trend'],
            methodology=regression_results['methodology']
        )
        return estimate

    
    def batch_estimate(
        self,
        locations: List[str],
        flat_types: List[str],
        exercise_date: str = "2025-10-01"
    ) -> List[PriceEstimate]:
        """perform batch estimation for multiple location-flat type combinations"""
        results = []
        
        for location in locations:
            for flat_type in flat_types:
                try:
                    estimate = self.estimate_cost(location, flat_type, exercise_date)
                    results.append(estimate)
                except Exception as e:
                    logger.error(f"Failed to estimate {flat_type} in {location}: {str(e)}")
        
        return results


def interactive_estimator(csv_path: Optional[str] = None):
    """interactive command-line interface for the estimator
    """
    if not csv_path:
        # resolve repo root from this file (agents/ -> repo root)
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        default_new = os.path.join(repo_root, "data", "bto_pricing_detail_cleaned.csv")
        default_old = os.path.join(repo_root, "bto_pricing_detail_cleaned.csv")
        csv_path = default_new if os.path.exists(default_new) else default_old
    
    try:
        estimator = EnhancedBTOCostEstimator(csv_path)
        print("\n" + "="*60)
        print("Enhanced BTO Cost Estimator")
        print("="*60)
        
        while True:
            print("\nEnter BTO project details (or 'quit' to exit):")
            
            location = input("Project location/town: ").strip()
            if location.lower() in ['quit', 'exit']:
                break
                
            flat_type = input("Flat type (e.g., 2-room, 3-room, 4-room, 5-room): ").strip()
            if flat_type.lower() in ['quit', 'exit']:
                break
            
            project_name = input("Project name (optional): ").strip() or None
            exercise_date = input("Exercise date (YYYY-MM-DD, default: 2025-10-01): ").strip() or "2025-10-01"
            
            print("\nProcessing... (This may take a moment)")
            
            try:
                estimate = estimator.estimate_cost(location, flat_type, exercise_date, project_name)
                
                print("\n" + "-"*50)
                print("ESTIMATION RESULTS")
                print("-"*50)
                print(f"Location: {estimate.project_location}")
                print(f"Flat Type: {estimate.flat_type}")
                print(f"Project Tier: {estimate.project_tier}")
                print(f"Exercise Date: {estimate.exercise_date}")
                print(f"Sample Size: {estimate.sample_size}")
                
                if estimate.estimated_price:
                    print(f"Estimated Price: ${estimate.estimated_price:,.0f}")
                    if estimate.confidence_interval[0] and estimate.confidence_interval[1]:
                        print(f"95% Confidence Interval: ${estimate.confidence_interval[0]:,.0f} - ${estimate.confidence_interval[1]:,.0f}")
                    print(f"Historical Trend: {estimate.historical_trend}")
                    print(f"Methodology: {estimate.methodology}")
                else:
                    print("Unable to generate estimate due to insufficient data")
                
            except Exception as e:
                print(f"Error generating estimate: {str(e)}")
                logger.error(f"Estimation error: {str(e)}", exc_info=True)
        
    except Exception as e:
        print(f"Failed to initialize estimator: {str(e)}")
        logger.error(f"Initialization error: {str(e)}", exc_info=True)


if __name__ == "__main__":
    interactive_estimator()
