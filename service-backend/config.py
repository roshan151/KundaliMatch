class Config:
    # Application Settings
    MAX_IMAGES = 8
    ALLOWED_FORMATS = {'jpeg', 'jpg', 'png'}
    KUNDALI_WEIGHT = 0.8
    PERSONAL_WEIGHT = 1-KUNDALI_WEIGHT
    TOTAL_GUN = 36
    MAX_MATCHES = 10
    SCORE_OUT_OF = 10
    MAX_GEOCODE_TIMEOUT = 15
    MAX_DESTINY_CHAT = 15
    MAX_NOTIFICATIONS = 50

    # Snowflake Configuration
    PROFILE_TABLE = "PROFILE_DB"
    PROFILE_TABLE_SCHEMA = "PUBLIC"
    PROFILE_TABLE_DATABASE = "LOVEBHAGYA"
    PROFILE_TABLE_WAREHOUSE = "COMPUTE_WH"
    MATCHING_TABLE = "MATCHING_TABLE"
    MATCHING_TABLE_SCHEMA = "PUBLIC"
    MATCHING_TABLE_DATABASE = "LOVEBHAGYA"
    MATCHING_TABLE_WAREHOUSE = "COMPUTE_WH"
    SNOWFLAKE_USERNAME = 'TeamKreative'
    SNOWFLAKE_ACCOUNT_ID = 'jkfvgpq-bk60648'

    # AWS Configuration
    BUCKET = 'match-bucket-2025'
    REGION = 'us-east-2'
    aws_secrets_group = 'ALIGNED_SECRET_ACCESS'
    encryption_and_twilio_group = 'ENCRYPTION_AND_TWILIO_ACCESS'

    # Service Configuration
    KUNDALI_SERVICE_URL = "http://kundali-service"
    KUNDALI_SERVICE_PORT = "8000"
    PROMPTS_YAML = 'prompts.yaml'
    OPENAI_MODEL_NAME = "gpt-4o-mini"

    # Twilio Configuration
    TWILIO_CHAT_SERVICE_SID = 'ISf6aecbd6aae748bfbb148db9efc45ce5'
    TWILIO_SERVICE_NAME = 'aligned-conversations' 

config = Config()