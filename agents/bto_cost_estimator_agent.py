import pandas as pd
import numpy as np

class CostEstimatorAgent:
    def __init__(self, historical_data_path=None):
        """
        Initialize the Cost Agent.
        If historical_data_path is None, use simulated dataset.
        """
        if historical_data_path:
            self.data = pd.read_csv(historical_data_path)
        else:
            # Simulated BTO historical data
            self.data = pd.DataFrame([
                {"estate": "Tengah Garden", "unit_type": "2-room", "price": 250000},
                {"estate": "Tengah Garden", "unit_type": "3-room", "price": 350000},
                {"estate": "Tengah Garden", "unit_type": "4-room", "price": 470000},
                {"estate": "Tengah Garden", "unit_type": "5-room", "price": 600000},
                {"estate": "Jurong West", "unit_type": "2-room", "price": 260000},
                {"estate": "Jurong West", "unit_type": "3-room", "price": 370000},
                {"estate": "Jurong West", "unit_type": "4-room", "price": 480000},
                {"estate": "Jurong West", "unit_type": "5-room", "price": 620000},
                {"estate": "Woodlands Edge", "unit_type": "2-room", "price": 240000},
                {"estate": "Woodlands Edge", "unit_type": "3-room", "price": 340000},
                {"estate": "Woodlands Edge", "unit_type": "4-room", "price": 460000},
                {"estate": "Woodlands Edge", "unit_type": "5-room", "price": 590000},
            ])
    
    def estimate_cost(self, estate: str, unit_type: str):
        """
        Estimate BTO cost based on estate and unit type.
        Returns min, max, median and notes.
        """
        df_filtered = self.data[
            (self.data["estate"].str.lower() == estate.lower()) & 
            (self.data["unit_type"].str.lower() == unit_type.lower())
        ]
        
        # If no exact match, fallback to same unit_type across all estates
        if df_filtered.empty:
            df_filtered = self.data[self.data["unit_type"].str.lower() == unit_type.lower()]
            notes = f"No historical data for {estate}, using similar unit types from other estates."
        else:
            notes = f"Based on previous BTO launches in {estate}."
        
        if df_filtered.empty:
            return {
                "estate": estate,
                "unit_type": unit_type,
                "estimated_price_range": "N/A",
                "median_price": "N/A",
                "notes": "No data available for this unit type."
            }
        
        min_price = df_filtered["price"].min()
        max_price = df_filtered["price"].max()
        median_price = int(df_filtered["price"].median())
        
        return {
            "estate": estate,
            "unit_type": unit_type,
            "estimated_price_range": f"${min_price:,} - ${max_price:,}",
            "median_price": f"${median_price:,}",
            "notes": notes
        }


# Example usage
if __name__ == "__main__":
    agent = CostEstimatorAgent()
    
    # User input example
    estate_input = input("Enter estate name: ")
    unit_type_input = input("Enter unit type (2-room, 3-room, etc.): ")
    
    estimate = agent.estimate_cost(estate_input, unit_type_input)
    
    print("\nBTO Cost Estimate:")
    print(f"Estate: {estimate['estate']}")
    print(f"Unit Type: {estimate['unit_type']}")
    print(f"Estimated Price Range: {estimate['estimated_price_range']}")
    print(f"Median Price: {estimate['median_price']}")
    print(f"Notes: {estimate['notes']}")
