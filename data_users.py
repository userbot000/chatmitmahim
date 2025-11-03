import requests
import json
import logging
from datetime import datetime, UTC

class NodeBBAPI:
    def __init__(self, verify_ssl: bool = True):
        self.session = requests.Session()
        self.base_url = "https://mitmachim.top"
        if not verify_ssl:
            self.session.verify = False
            import urllib3
            urllib3.disable_warnings()
            
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Origin': self.base_url,
            'Referer': f"{self.base_url}/",
            'X-Requested-With': 'XMLHttpRequest'
        }
        self.logger = logging.getLogger('NodeBBAPI')
        self.user_data = None

    def login(self, username: str, password: str) -> bool:
        try:
            config_response = self.session.get(
                f"{self.base_url}/api/config",
                headers=self.headers
            )
            config_data = config_response.json()
            csrf_token = config_data.get('csrf_token')
            if csrf_token:
                self.headers['x-csrf-token'] = csrf_token

            login_data = {
                "username": username,
                "password": password
            }
            
            login_response = self.session.post(
                f"{self.base_url}/api/v3/utilities/login",
                json=login_data,
                headers=self.headers
            )
            
            if login_response.ok:
                response_data = login_response.json()
                self.user_data = response_data.get('response', {})
                self.logger.info(f"התחברות מוצלחת עבור המשתמש {username}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"שגיאת התחברות: {str(e)}")
            return False

    def send_chat_message(self, room_id: str, message: str) -> dict:
        if not self.user_data:
            self.logger.error("נדרשת התחברות לפני שליחת הודעה")
            return None

        try:
            config_response = self.session.get(
                f"{self.base_url}/api/config",
                headers=self.headers
            )
            config_data = config_response.json()
            csrf_token = config_data.get('csrf_token')
            if csrf_token:
                self.headers['x-csrf-token'] = csrf_token

            data = {
                "roomId": room_id,
                "message": message,
                "_csrf": csrf_token
            }

            response = self.session.post(
                f"{self.base_url}/api/v3/chats/{room_id}",
                json=data,
                headers=self.headers
            )

            if response.ok:
                return response.json()
            else:
                self.logger.error(f"שגיאה בשליחת הודעת צ'אט: {response.status_code}")
                self.logger.error(f"תוכן התשובה: {response.text}")
                return None

        except Exception as e:
            self.logger.error(f"שגיאה בשליחת הודעת צ'אט: {str(e)}")
            return None


class YemotAPI:
    def __init__(self, system_number, password):
        self.base_url = "https://www.call2all.co.il/ym/api/"
        self.system_number = system_number
        self.password = password
        self.token = None

    def login(self):
        try:
            params = {
                'username': self.system_number,
                'password': self.password
            }
            
            response = requests.get(f"{self.base_url}Login", params=params)
            data = response.json()
            print("תגובת התחברות:", data)
            
            if data.get("responseStatus") == "OK":
                self.token = data.get("token")
                return True
            return False
            
        except Exception as e:
            print(f"שגיאה בהתחברות: {str(e)}")
            return False

    def parse_ymgr_file(self, full_path):
        if not self.token:
            print("נא להתחבר תחילה!")
            return None

        try:
            params = {
                'token': self.token,
                'wath': full_path,
                'convertType': 'json',
                'notLoadLang': 0,
                'renderLanguage': 'HE'
            }
            
            print(f"שולח בקשה לקובץ: {full_path}")
            print(f"פרמטרים: {params}")
            
            response = requests.get(f"{self.base_url}RenderYMGRFile", params=params)
            print(f"URL מלא: {response.url}")
            
            data = response.json()
            print(f"תגובת השרת: {data}")
            
            if data.get("responseStatus") == "OK":
                # הנתונים מגיעים כבר כ-JSON במערך data
                records = data.get("data", [])
                if records:
                    return records
                else:
                    print("לא נמצאו רשומות בקובץ")
                    return None
            else:
                error_msg = data.get('message', 'שגיאה לא ידועה')
                print(f"שגיאה בתגובת השרת: {error_msg}")
                return None
                
        except Exception as e:
            print(f"שגיאה בפענוח קובץ YMGR: {str(e)}")
            return None

        
    def get_room_id(self, base_path):
        """
        מחלץ את מזהה החדר מקובץ 000.TTS
        :param base_path: הנתיב הבסיסי (לדוגמא: ivr2:5/1/1)
        :return: מזהה החדר או None אם לא נמצא
        """
        try:
            tts_path = f"{base_path}/000.tts"
            params = {
                'token': self.token,
                'what': tts_path  # שימוש ב-what במקום filename/wath
            }
            
            print(f"קורא קובץ TTS מהנתיב: {tts_path}")
            
            # שימוש ב-GetTextFile
            response = requests.get(f"{self.base_url}GetTextFile", params=params)
            print(f"URL מלא: {response.url}")
            print(f"סטטוס התגובה: {response.status_code}")
            
            data = response.json()
            
            # בודק אם יש תוכן בקובץ
            if 'contents' in data:
                content = data['contents']
                print("\n=== תוכן קובץ TTS ===")
                print(content)
                print("=====================\n")
                
                if isinstance(content, str):
                    # חיפוש מספר בן 5 ספרות
                    import re
                    matches = re.findall(r'\d{5}', content)
                    if matches:
                        room_id = matches[0]
                        print(f"נמצא מזהה חדר: {room_id}")
                        return room_id
                    else:
                        print("לא נמצא מספר בן 5 ספרות בקובץ")
                        print("תוכן הקובץ המלא:")
                        print(content)
            else:
                print("לא נמצא תוכן בקובץ")
                print("תגובת השרת המלאה:")
                print(data)
                
            return None
            
        except Exception as e:
            print(f"שגיאה בקריאת קובץ TTS: {str(e)}")
            print(f"פרטי השגיאה המלאים:")
            import traceback
            print(traceback.format_exc())
            return None
    
def main():
    # יצירת חיבור למערכת
    ymot_api = YemotAPI("0747098744", "123456")
    
    # התחברות
    if not ymot_api.login():
        print("ההתחברות נכשלה")
        return
        
    print("התחברות הצליחה!")
    
    # קריאת מזהה החדר
    room_id = ymot_api.get_room_id("ivr2:5/1/2")
    if not room_id:
        print("לא נמצא מזהה חדר")
        return
    
    print(f"מזהה החדר שנמצא: {room_id}")
    
    # קריאת נתונים משלוחה 5
    extension_5_data = ymot_api.parse_ymgr_file("ivr2:5/1/2/Hash/ApprovalAll.ymgr")
    if not extension_5_data:
        print("לא נמצאו נתונים בשלוחה 5")
        return

    # קריאת נתונים משלוחה 7
    extension_7_data = ymot_api.parse_ymgr_file("ivr2:7/ApprovalAll.ymgr")
    if not extension_7_data:
        print("לא נמצאו נתונים בשלוחה 7")
        return

    # יצירת חיבור ל-NodeBB
    nodebb_api = NodeBBAPI(verify_ssl=False)

    print("\n=== התאמת נתונים ושליחת הודעות ===")
    for record_5 in extension_5_data:
        phone_5 = record_5.get('טלפון')
        message = record_5.get('P050')  # תוכן ההודעה מ-P050
        
        if not phone_5 or not message:
            continue

        # חיפוש הטלפון בנתוני שלוחה 7
        for record_7 in extension_7_data:
            if record_7.get('טלפון') == phone_5:
                username = record_7.get('P050')
                password = record_7.get('P051')
                
                print(f"\nנמצאה התאמה עבור טלפון: {phone_5}")
                print(f"שם משתמש: {username}")
                print(f"סיסמא: {password}")
                print(f"תוכן ההודעה: {message}")
                print(f"מזהה חדר: {room_id}")
                
                # שליחת ההודעה לצ'אט
                if username and password and room_id and message:
                    if nodebb_api.login(username, password):
                        response = nodebb_api.send_chat_message(room_id, message)
                        if response:
                            print(f"ההודעה נשלחה בהצלחה!")
                        else:
                            print("שליחת ההודעה נכשלה")
                    else:
                        print(f"ההתחברות ל-NodeBB נכשלה עבור המשתמש {username}")
                break


if __name__ == "__main__":
    main()
