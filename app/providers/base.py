import logging
from typing import List, Any

class ProviderFallbackManager:
    """
    Executes a requested method across a list of providers (Primary -> Alternative).
    Stops and returns data on the first successful response.
    """
    @staticmethod
    async def execute(providers: List[Any], method_name: str, *args, **kwargs) -> Any:
        errors = []
        for index, provider in enumerate(providers):
            provider_name = provider.__class__.__name__
            try:
                func = getattr(provider, method_name)
                logging.info(f"Attempting {method_name} via {provider_name} (Priority {index + 1})")
                
                result = await func(*args, **kwargs)
                
                # If the provider explicitly returns an error dict, treat it as a failure
                if isinstance(result, dict) and "error" in result:
                    raise Exception(result["error"])
                    
                return result
                
            except Exception as e:
                logging.warning(f"Provider {provider_name} failed: {str(e)}")
                errors.append(f"{provider_name}: {str(e)}")
                continue 
                
        return {"error": f"All providers failed. Details: { ' | '.join(errors) }"}