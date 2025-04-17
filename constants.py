"""
Constants for the TMS system.
This file contains all the constants and default values used in the TMS system.
"""

class Constants:
    """Constants used in the TMS system."""
    
    # Stop types
    PICKUP_STOP_TYPE = "PUP"
    DELIVERY_STOP_TYPE = "DRP"
    
    # Event codes
    PICKUP_EVENT_CODE = "LLD"
    DELIVERY_EVENT_CODE = "LUL"
    
    # Trailer types
    TRAILER_TYPE_FLAT = "FLAT"
    TRAILER_TYPE_REEFER = "REEFER"
    TRAILER_TYPE_VAN = "VAN"
    
    # Rev types
    REV_TYPE1_LOGCOM = "LOGCOM"
    REV_TYPE1_LOGOUT = "LOGOUT"
    REV_TYPE1_STAND = "STAND"
    
    REV_TYPE2_HOUSE = "HOUSE"
    REV_TYPE2_CZ = "CZ"
    REV_TYPE2_JBEMIS = "JBEMIS"
    REV_TYPE2_STD = "STD"
    REV_TYPE2_STI = "STI"
    REV_TYPE2_STO = "STO"
    
    REV_TYPE3_IN = "IN"
    REV_TYPE3_OUT = "OUT"
    REV_TYPE3_GSTET = "GSTET"
    REV_TYPE3_JCLAY = "JCLAY"
    REV_TYPE3_JKOPP = "JKOPP"
    REV_TYPE3_LPATE = "LPATE"
    REV_TYPE3_SCAMP = "SCAMP"
    
    REV_TYPE4_LOCAL = "LOCAL"
    REV_TYPE4_MDWST = "MDWST"
    REV_TYPE4_OTR = "OTR"
    REV_TYPE4_FLAT = "FLAT"
    REV_TYPE4_MILES = "MILES"
    
    # ExtraInfo types
    EXTRA_INFO1_CONT = "CONT"
    EXTRA_INFO1_STOPGO = "STOPGO"
    
    # Reference number types
    REF_BL = "BL#"
    REF_LOAD = "LOAD"
    REF_PO = "PO#"
    REF_PU = "PU#"
    REF_REF = "REF"
    REF_SID = "SID"
    
    # Order status
    ORDER_STATUS_AVAILABLE = "AVL"
    
    # Charge item codes
    CHARGE_ITEM_CODE_LHF = "LHF"
    
    # Charge rate units
    CHARGE_RATE_UNIT_FLT = "FLT"
    
    # Temperature units
    TEMPERATURE_UNITS_FRNHGT = "Frnhgt"
    
    # Commodities
    COMMODITY_BRICK = "BRICK"
    COMMODITY_BUILDING = "BUILDING"
    COMMODITY_DRYFOOD = "DRYFOOD"
    COMMODITY_FAK = "FAK"
    COMMODITY_FRZFOOD = "FRZFOOD"
    COMMODITY_FZNRFR = "FZN&RFR"
    COMMODITY_REFOOD = "REFOOD"
    COMMODITY_STEEL = "STEEL"
    COMMODITY_STONE = "STONE"
    
    # Weight units
    WEIGHT_UNIT_LBS = "LBS"
    
    # Currency
    CURRENCY_US = "US$"
    
    # Time format for TMS
    TMS_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.000Z"
    
    # Default values
    DEFAULT_RATE = 111.11
    ZELLER_MILEAGE_THRESHOLDS = 0.255
    ZELLER_MILEAGE_RATE = 0.51
    ZELLER_HOME_STATE = "WI"

    # Equipment type mapping
    EQUIPMENT_TYPE_MAPPING = {
        "Van": TRAILER_TYPE_VAN,
        "Reefer": TRAILER_TYPE_REEFER,
        "Flat": TRAILER_TYPE_FLAT,
        "53VR": TRAILER_TYPE_VAN,  # Assuming 53' Van or Reefer defaults to Van
    }
    
    # Reference type mapping
    REFERENCE_TYPE_MAPPING = {
        "PO": REF_PO,
        "BL": REF_BL,
        "LOAD": REF_LOAD,
        "PU": REF_PU,
        "REF": REF_REF,
        "SID": REF_SID,
    }

    # Customer to commodity mapping (example)
    CUSTOMER_COMMODITY_MAPPING = {
        "KIRSCH": COMMODITY_DRYFOOD,
        "ZELLER": COMMODITY_FAK,
        # Add more mappings as needed
    }