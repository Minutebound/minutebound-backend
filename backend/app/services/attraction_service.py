import httpx
from app.schemas.attraction import Attraction

class AttractionService:
    
    async def get_attractions(self, lat: float, lon: float, radius_miles: int = 30):
        print(f"🔍 [ATTRACTIONS] CACHE MISS: Fetching OSM data for {lat}, {lon}")
        radius_meters = int(radius_miles * 1609.34)
        url = "https://overpass.kumi.systems/api/interpreter"
        
        query = f"""
        [out:json][timeout:25];
        (
          node["amenity"~"restaurant|cafe|pub"](around:{radius_meters},{lat},{lon});
          node["leisure"~"park|golf_course"](around:{radius_meters},{lat},{lon});
          node["historic"="monument"](around:{radius_meters},{lat},{lon});
          node["tourism"~"hotel|museum|attraction|viewpoint|zoo"](around:{radius_meters},{lat},{lon});
        );
        out body; 
        """

        async with httpx.AsyncClient() as client:
            try:
                print(f"🗺️ Fetching attractions with coordinates near {lat}, {lon}")
                response = await client.post(url, data=query, timeout=30.0)
                
                if response.status_code != 200:
                    return {"error": "OSM Overpass API is currently busy or unavailable."}
                
                elements = response.json().get("elements", [])
                clean_attractions = []
                
                for item in elements:
                    tags = item.get("tags", {})
                    name = tags.get("name")
                    
                    if not name: continue

                    full_addr = tags.get("addr:full")
                    street = tags.get("addr:street")
                    house = tags.get("addr:housenumber")
                    city = tags.get("addr:city")
                    
                    if full_addr:
                        address = full_addr
                    elif street and house:
                        address = f"{house} {street}" + (f", {city}" if city else "")
                    elif street:
                        address = f"{street}" + (f", {city}" if city else "")
                    else:
                        continue 

                    category = "Other"
                    attr_type = "Unknown"
                    if "amenity" in tags:
                        category = "Amenity"
                        attr_type = tags["amenity"].replace("_", " ").title()
                    elif "leisure" in tags:
                        category = "Leisure"
                        attr_type = tags["leisure"].replace("_", " ").title()
                    elif "historic" in tags:
                        category = "Historic"
                        attr_type = tags["historic"].title()
                    elif "tourism" in tags:
                        category = "Tourism"
                        attr_type = tags["tourism"].replace("_", " ").title()

                    clean_attractions.append(Attraction(
                        id=item.get("id"),
                        name=name,
                        category=category,
                        attraction_type=attr_type,
                        address=address,
                        website=tags.get("website") or tags.get("contact:website"),
                        opening_hours=tags.get("opening_hours"),
                        latitude=item.get("lat"),  
                        longitude=item.get("lon") 
                    ))
                    
                clean_attractions.sort(key=lambda x: (x.category, x.name))
                    
                return clean_attractions
                
            except Exception as e:
                return {"error": f"Connection Error: {str(e)}"}

attraction_service = AttractionService()