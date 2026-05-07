from fastapi import APIRouter, Request

router = APIRouter()

@router.get("/top")
async def get_top_destinations(request: Request):
    """Returns the top 5 most searched destinations."""
    try:
        top_destinations = await request.app.state.redis.zrevrange("top_destinations", 0, 4, withscores=True)
        
        results = []
        for dest, count in top_destinations:
            parts = dest.split(", ")
            city = parts[0]
            state = parts[1] if len(parts) > 1 else ""
            
            results.append({
                "city": city,
                "state": state,
                "full_name": dest,
                "searches": int(count)
            })
            
        return results
    except Exception as e:
        print(f"[Redis] Failed to fetch top destinations: {e}")
        return []