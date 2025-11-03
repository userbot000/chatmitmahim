import requests
import json
import logging
from itertools import product
from datetime import datetime
import time
from urllib3.exceptions import InsecureRequestWarning



def my_where():
    return r'C:\ProgramData\NetFree\CA\netfree-ca-list.crt'
requests.certs.where = my_where
# ביטול אזהרות SSL
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

class NodeBBAPI:
    def __init__(self, verify_ssl=True):
        self.base_url = "https://mitmachim.top"
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.logger = logging.getLogger(__name__)
        
        # הוספת headers חיוניים
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'he,en-US;q=0.7,en;q=0.3',
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': 'https://forum.tora.ws',
            'Referer': 'https://forum.tora.ws/'
        })

    def login(self, username, password):
        """התחברות למערכת NodeBB"""
        try:
            # קודם כל מקבלים את ה-CSRF token
            csrf_response = self.session.get(f"{self.base_url}/api/config", verify=self.verify_ssl)
            if csrf_response.status_code == 200:
                csrf_token = csrf_response.json().get('csrf_token')
                self.session.headers.update({'X-CSRF-Token': csrf_token})
            
            login_url = f"{self.base_url}/login"
            data = {
                'username': username,
                'password': password,
                'remember': 'on'
            }
            
            response = self.session.post(login_url, json=data, verify=self.verify_ssl)
            if response.status_code == 200:
                self.logger.info(f"התחברות הצליחה עבור משתמש: {username}")
                return True
            else:
                self.logger.error(f"התחברות נכשלה. קוד: {response.status_code}, תגובה: {response.text}")
                return False
            
        except Exception as e:
            self.logger.error(f"שגיאה בהתחברות ל-NodeBB: {str(e)}")
            return False

    def send_chat_message(self, room_id, message):
        """שליחת הודעת צ'אט"""
        try:
            chat_url = f"{self.base_url}/api/v3/chats/{room_id}"
            data = {
                'message': message,
                'timestamp': int(time.time() * 1000)
            }
            
            response = self.session.post(chat_url, json=data, verify=self.verify_ssl)
            return response.status_code == 200
            
        except Exception as e:
            self.logger.error(f"שגיאה בשליחת הודעת צ'אט: {str(e)}")
            return False

class YemotAPI:
    def __init__(self, system_number, password):
        self.base_url = "https://www.call2all.co.il/ym/api/"
        self.system_number = system_number
        self.password = password
        self.token = None
        
        # הגדרת logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename=f'ymot_chat_sender_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        )
        self.logger = logging.getLogger(__name__)

    def login(self):
        """התחברות למערכת ימות"""
        try:
            params = {
                'username': self.system_number,
                'password': self.password
            }
            
            response = requests.get(f"{self.base_url}Login", params=params)
            data = response.json()
            self.logger.info(f"תגובת התחברות: {data}")
            
            if data.get("responseStatus") == "OK":
                self.token = data.get("token")
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"שגיאה בהתחברות: {str(e)}")
            return False

    def get_room_id(self, base_path):
        """מחלץ את מזהה החדר מקובץ 000.TTS"""
        try:
            tts_path = f"{base_path}/000.tts"
            params = {
                'token': self.token,
                'what': tts_path
            }
            
            self.logger.info(f"קורא קובץ TTS מהנתיב: {tts_path}")
            
            response = requests.get(f"{self.base_url}GetTextFile", params=params)
            data = response.json()
            
            if 'contents' in data:
                content = data['contents']
                self.logger.debug(f"תוכן קובץ TTS: {content}")
                
                if isinstance(content, str):
                    import re
                    matches = re.findall(r'\d{5}', content)
                    if matches:
                        room_id = matches[0]
                        self.logger.info(f"נמצא מזהה חדר: {room_id}")
                        return room_id
            
            return None
            
        except Exception as e:
            self.logger.error(f"שגיאה בקריאת קובץ TTS: {str(e)}")
            return None

    def parse_ymgr_file(self, full_path):
        """קורא ומפרסר קובץ YMGR"""
        if not self.token:
            self.logger.warning("נא להתחבר תחילה!")
            return None

        try:
            params = {
                'token': self.token,
                'wath': full_path,
                'convertType': 'json',
                'notLoadLang': 0,
                'renderLanguage': 'HE'
            }
            
            response = requests.get(f"{self.base_url}RenderYMGRFile", params=params)
            data = response.json()
            
            if data.get("responseStatus") == "OK":
                records = data.get("data", [])
                if records:
                    return records
                else:
                    self.logger.warning(f"לא נמצאו רשומות בקובץ: {full_path}")
                    return None
            else:
                error_msg = data.get('message', 'שגיאה לא ידועה')
                self.logger.error(f"שגיאה בתגובת השרת: {error_msg}")
                return None
                
        except Exception as e:
            self.logger.error(f"שגיאה בפענוח קובץ YMGR: {str(e)}")
            return None



    def delete_ymgr_file(self, full_path):
        """מוחק קובץ YMGR מהשרת"""
        try:
            if not self.token:
                self.logger.warning("נא להתחבר תחילה!")
                return False

            # Construct the correct API endpoint and parameters
            params = {
                'token': self.token,
                'action': 'delete',
                'what0': full_path  # Using what0 for single file deletion
            }
            
            self.logger.info(f"מנסה למחוק קובץ: {full_path}")
            self.logger.debug(f"URL: {self.base_url}FileAction")  # Changed to FileAction endpoint
            self.logger.debug(f"Parameters: {params}")
            
            # Use the FileAction endpoint
            response = requests.get(f"{self.base_url}FileAction", params=params)
            self.logger.debug(f"Response Status Code: {response.status_code}")
            self.logger.debug(f"Response Content: {response.text}")
            
            data = response.json()
            
            # Check the success flag in the response
            if data.get("success") is True:  # Changed to check the success boolean flag
                self.logger.info(f"הקובץ {full_path} נמחק בהצלחה")
                return True
            else:
                error_msg = data.get('message', 'שגיאה לא ידועה')
                self.logger.error(f"שגיאה במחיקת הקובץ: {error_msg}")
                self.logger.error(f"Response Data: {data}")
                return False
                
        except Exception as e:
            self.logger.error(f"שגיאה במחיקת קובץ YMGR: {str(e)}")
            return False      

    def process_path(self, path_pattern, room_id):
        """מעבד נתיב ספציפי ושולח צ'אטים"""
        try:
            extension_5_data = self.parse_ymgr_file(path_pattern)
            if not extension_5_data:
                return

            extension_7_data = self.parse_ymgr_file("ivr2:7/ApprovalAll.ymgr")
            if not extension_7_data:
                return

            # יצירת מופע NodeBB API
            nodebb_api = NodeBBAPI(verify_ssl=False)

            messages_sent = False  # דגל לסימון האם נשלחו הודעות מהקובץ

            for record_5 in extension_5_data:
                phone_5 = record_5.get('טלפון')
                message = record_5.get('P050')
                
                if not phone_5 or not message:
                    continue

                for record_7 in extension_7_data:
                    if record_7.get('טלפון') == phone_5:
                        username = record_7.get('P050')
                        password = record_7.get('P051')
                        
                        self.logger.info(f"\nשולח צ'אט עבור:")
                        self.logger.info(f"טלפון: {phone_5}")
                        self.logger.info(f"שם משתמש: {username}")
                        self.logger.info(f"תוכן: {message}")
                        self.logger.info(f"מזהה חדר: {room_id}")
                        
                        # התחברות ושליחת הצ'אט
                        if nodebb_api.login(username, password):
                            if nodebb_api.send_chat_message(room_id, message):
                                self.logger.info("הצ'אט נשלח בהצלחה!")
                                messages_sent = True  # מסמן שנשלחה לפחות הודעה אחת מהקובץ
                            else:
                                self.logger.error("שגיאה בשליחת הצ'אט")
                        else:
                            self.logger.error(f"שגיאה בהתחברות למשתמש {username}")
                        
                        time.sleep(1)
                        break

            # מחיקת הקובץ רק אם נשלחו ממנו הודעות בהצלחה
            if messages_sent:
                self.logger.info(f"מנסה למחוק את הקובץ {path_pattern} לאחר שליחת ההודעות")
                if self.delete_ymgr_file(path_pattern):
                    self.logger.info(f"הקובץ {path_pattern} נמחק בהצלחה")
                else:
                    self.logger.error(f"שגיאה במחיקת הקובץ {path_pattern}")

        except Exception as e:
            self.logger.error(f"שגיאה בעיבוד נתיב {path_pattern}: {str(e)}")
        

    def scan_all_paths(self):
        """סורק את כל הנתיבים האפשריים ושולח צ'אטים"""
        self.logger.info("מתחיל סריקת נתיבים...")
        
        # הוספת timestamp לתחילת הריצה
        current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        self.logger.info(f"Start Time (UTC): {current_time}")
        
        # יצירת כל הקומבינציות האפשריות של המספרים
        for i in range(1, 11):  # מ-1 עד 10
            for j in range(1, 11):  # מ-1 עד 10
                base_path = f"ivr2:5/{i}/{j}"
                path_pattern = f"{base_path}/Hash/ApprovalAll.ymgr"
                
                self.logger.info(f"\nבודק נתיב: {path_pattern}")
                
                # קבלת מזהה חדר
                room_id = self.get_room_id(base_path)
                if room_id:
                    self.logger.info(f"מעבד נתיב עם מזהה חדר: {room_id}")
                    self.process_path(path_pattern, room_id)
                
                # המתנה קצרה בין בקשות
                time.sleep(0.5)

        # הוספת timestamp לסיום הריצה
        end_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        self.logger.info(f"End Time (UTC): {end_time}")

def main():
    # יצירת חיבור למערכת
    ymot_api = YemotAPI("0747098744", "123456")
    
    # התחברות
    if not ymot_api.login():
        print("ההתחברות נכשלה")
        return
        
    print("התחברות הצליחה!")
    
    # סריקת כל הנתיבים האפשריים
    ymot_api.scan_all_paths()

if __name__ == "__main__":
    main()
