from sqlalchemy import create_engine,text
import os
from dotenv import load_dotenv

load_dotenv()

PASSWORD = os.environ.get('password')

DATABASE_URL = f"postgresql://postgres.dlbtacxmxlgsjvmtrlsl:{PASSWORD}@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres"

engine = create_engine(DATABASE_URL)

def get_user_friends(user_id):
    query = '''SELECT u.unique_id
            FROM friends f
            JOIN users u 
            ON u.unique_id = CASE 
                WHEN f.user1_id = :user_id THEN f.user2_id
                ELSE f.user1_id
            END
            WHERE f.user1_id = :user_id OR f.user2_id = :user_id;
            '''
    param = {
        'user_id' : user_id
    }
    try:
        with engine.connect() as conn:
            friends = conn.execute(text(query),parameters=param).fetchall()
            # print(friends)
        return friends
    except Exception as e:
        print(e)
        return []

def save_user_device(user_id, token, device_type, device_name):

    query = """
    INSERT INTO user_devices (
        user_id,
        fcm_token,
        device_type,
        device_name,
        last_used
    )
    VALUES (
        :user_id,
        :token,
        :device_type,
        :device_name,
        NOW()
    )
    ON CONFLICT (fcm_token)
    DO UPDATE SET
        user_id = EXCLUDED.user_id,
        device_type = EXCLUDED.device_type,
        device_name = EXCLUDED.device_name,
        last_used = NOW();
    """

    params = {
        "user_id": user_id,
        "token": token,
        "device_type": device_type,
        "device_name": device_name
    }

    try:
        with engine.connect() as conn:
            conn.execute(text(query), params)
            conn.commit()
        return True

    except Exception as e:
        print(e)
        return False
    

def get_user_tokens(user_id):

    query = """
    SELECT fcm_token
    FROM user_devices
    WHERE user_id = :user_id;
    """

    try:
        with engine.connect() as conn:
            result = conn.execute(text(query), {"user_id": user_id}).fetchall()

        return [row[0] for row in result]

    except Exception as e:
        print(e)
        return []


def delete_token(token):

    query = """
    DELETE FROM user_devices
    WHERE fcm_token = :token;
    """

    try:
        with engine.connect() as conn:
            conn.execute(text(query), {"token": token})
            conn.commit()
        return True

    except Exception as e:
        print(e)
        return False
