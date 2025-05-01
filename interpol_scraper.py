import time
from pprint import pprint
from deutschland import interpol
from deutschland.interpol.api import default_api
from deutschland.interpol.model.red_notices import RedNotices

# Set configuration (optional because it's the default, but shown for clarity)
configuration = interpol.Configuration(
    host="https://ws-public.interpol.int"
)
import time
from pprint import pprint
from deutschland import interpol
from deutschland.interpol.api import default_api
from deutschland.interpol.model.red_notices import RedNotices
from deutschland.interpol.rest import ApiException

# Set configuration
configuration = interpol.Configuration(
    host="https://ws-public.interpol.int"
)

# Add custom headers (IMPORTANT!)
configuration.api_key_prefix['Authorization'] = 'Bearer'
configuration.api_key['Authorization'] = ''
configuration.default_headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

# Use the API client inside a context
with interpol.ApiClient(configuration) as api_client:
    api_instance = default_api.DefaultApi(api_client)

    try:
        api_response: RedNotices = api_instance.notices_v1_red_get(
            page=1,
            result_per_page=10
        )
        pprint(api_response.to_dict())

    except ApiException as e:
        print("Exception when calling DefaultApi->notices_v1_red_get: %s\n" % e)


# Use the API client inside a context
with interpol.ApiClient(configuration) as api_client:
    # Create API instance
    api_instance = default_api.DefaultApi(api_client)
    
    # (Optional) You can set search parameters
    forename = "MAX"  # First name
    name = "MUSTERMANN"  # Last name
    nationality = "DE"  # German nationality
    age_min = 18
    age_max = 120
    free_text = ""
    sex_id = "M"  # "M" or "F"
    arrest_warrant_country_id = "DE"
    page = 1
    result_per_page = 10

    try:
        # Fetch Red Notices
        api_response: RedNotices = api_instance.notices_v1_red_get(
            forename=forename,
            name=name,
            nationality=nationality,
            age_max=age_max,
            age_min=age_min,
            free_text=free_text,
            sex_id=sex_id,
            arrest_warrant_country_id=arrest_warrant_country_id,
            page=page,
            result_per_page=result_per_page
        )
        
        # Print the response nicely
        pprint(api_response.to_dict())
    
    except interpol.ApiException as e:
        print("Exception when calling DefaultApi->notices_v1_red_get: %s\n" % e)
