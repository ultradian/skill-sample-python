"""services.py: aws services for lambda tone therapy skill."""
import boto3
from constants import DB_TABLE_NAME

DYNAMODB = boto3.resource('dynamodb', region_name='us-east-1')
DB_TABLE = DYNAMODB.Table(DB_TABLE_NAME)

