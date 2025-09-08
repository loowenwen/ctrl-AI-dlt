// Interface for price estimate response
export interface PriceEstimate {
  price_range: string;
  affordability_status: string;
  reason?: string;
}

// Function to get price estimate from the backend
export async function getPriceEstimate(projectName: string, flatType: string): Promise<PriceEstimate> {
  try {
    const response = await fetch(`/api/estimate-price/${encodeURIComponent(projectName)}/${encodeURIComponent(flatType)}`);
    
    if (!response.ok) {
      throw new Error('Failed to fetch price estimate');
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error fetching price estimate:', error);
    throw error;
  }
}
