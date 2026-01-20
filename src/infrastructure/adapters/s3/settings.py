from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AWSS3Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AWS_S3_")

    endpoint_url: str
    access_key_id: str
    secret_access_key: SecretStr
    protected_bucket_name: str = "protected"
    public_bucket_name: str = "public"
