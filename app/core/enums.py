import enum

class GenderEnum(str, enum.Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    PREFER_NOT_TO_SAY = "PREFER_NOT_TO_SAY"
    OTHER = "OTHER"

    @classmethod
    def list_all(cls):
        """Returns all gender options as a list of strings."""
        return [e.value for e in cls]

class VisibilityEnum(str, enum.Enum):
    PRIVATE = "PRIVATE"
    PUBLIC = "PUBLIC"

    @classmethod
    def list_all(cls):
        """Returns all visibility options as a list of strings."""
        return [e.value for e in cls]

class UserRole(str, enum.Enum):
    USER = "USER"
    SUPPORT = "SUPPORT"
    ADMIN = "ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"

    @classmethod
    def list_all(cls):
        """Returns all user roles as a list of strings."""
        return [e.value for e in cls]

class DevicePlatform(str, enum.Enum):
    WEB = "WEB"
    IOS = "IOS"
    ANDROID = "ANDROID"
    UNKNOWN = "UNKNOWN"
    
    @classmethod
    def list_all(cls):
        """Returns all device platforms as a list of strings."""
        return [e.value for e in cls]

class PlaceType(str, enum.Enum):
    COUNTRY = "country"
    STATE = "state"
    REGION = "region"
    COUNTY = "county"
    CITY = "city"
    TOWN = "town"
    VILLAGE = "village"

    @classmethod
    def list_all(cls):
        """Returns all OSM place types as a list of strings."""
        return [e.value for e in cls]

class EventCategory(str, enum.Enum):
    # Music & Performing Arts
    CONCERT_LIVE_MUSIC = "Concert & Live Music"
    THEATRE_ARTS = "Theatre & Visual Arts"
    COMEDY = "Comedy"
    FESTIVAL = "Festival"
    
    # Sports & Outdoors
    SPORTS_PRO = "Professional Sports"
    SPORTS_AMATEUR = "Amateur/Local Sports"
    OUTDOORS_ADVENTURE = "Outdoors & Adventure"
    HEALTH_WELLNESS = "Health & Wellness"
    
    # Food & Drink
    FOOD_DINING = "Food & Dining"
    WINE_BEER_SPIRITS = "Wine, Beer & Spirits"
    FARMERS_MARKET = "Farmers Market"
    
    # Community & Culture
    COMMUNITY_CULTURE = "Community & Culture"
    FAIRS_EXPOS = "Fairs & Expos"
    CHARITY_CAUSES = "Charity & Causes"
    SEASONAL_HOLIDAY = "Seasonal & Holiday"
    RELIGIOUS_SPIRITUAL = "Religious & Spiritual"
    
    # Business & Tech
    BUSINESS_NETWORKING = "Business & Networking"
    CONFERENCE_TRADESHOW = "Conference & Trade Show"
    TECH_INNOVATION = "Tech & Innovation"
    EDUCATION_WORKSHOP = "Education & Workshop"
    
    # Lifestyle
    FAMILY_KIDS = "Family & Kids"
    NIGHTLIFE_SINGLES = "Nightlife & Singles"
    GAMING_ESPORTS = "Gaming & Esports"
    HOBBIES_SPECIAL_INTEREST = "Hobbies & Special Interest"
    FASHION_BEAUTY = "Fashion & Beauty"

    @classmethod
    def list_all(cls):
        """Returns all event categories as a list of strings."""
        return [e.value for e in cls]
    

class BookingStatus(str, enum.Enum):
    CANCELLED = "CANCELLED"
    CONFIRMED = "CONFIRMED"
    PENDING = "PENDING"

    @classmethod
    def list_all(cls):
        """Returns all booking statuses as a list of strings."""
        return [e.value for e in cls]

class BookingType(str, enum.Enum):
    CAR_RENTAL = "CAR_RENTAL"
    FLIGHT = "FLIGHT"
    HOTEL = "HOTEL"
    TOUR = "TOUR"

    @classmethod
    def list_all(cls):
        """Returns all booking types as a list of strings."""
        return [e.value for e in cls]