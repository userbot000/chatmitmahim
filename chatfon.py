import requests
import urllib3
from bs4 import BeautifulSoup
from datetime import datetime
import re
import time
import json

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def my_where():
    return r'C:\\ProgramData\\NetFree\\CA\\netfree-ca-list.crt'
requests.certs.where = my_where

class NodeBBAPI:
    def __init__(self):
        self.session = requests.Session()
        self.session.verify = False
        self.base_url = "https://mitmachim.top"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }

    def login(self, username, password):
        """התחברות לפורום"""
        try:
            self.username = username
            print("מתחבר לפורום...")
            login_data = {
                "username": username,
                "password": password
            }
            
            login_response = self.session.post(
                f"{self.base_url}/api/v3/utilities/login",
                json=login_data,
                headers=self.headers
            )
            
            print(f"קוד תשובת התחברות: {login_response.status_code}")
            print(f"תוכן תשובת התחברות: {login_response.text[:200]}")
            
            if login_response.ok:
                response_data = login_response.json()
                if response_data.get('status', {}).get('code') == 'ok':
                    user_data = response_data.get('response', {})
                    self.userslug = user_data.get('userslug')  # שמירת ה-userslug
                    self.session.cookies.update(login_response.cookies)
                    print(f"התחברות לפורום הצליחה! userslug: {self.userslug}")
                    return True
                    
            print("התחברות לפורום נכשלה")
            return False
            
        except Exception as e:
            print(f"שגיאה בהתחברות לפורום: {str(e)}")
            return False
    def get_chat_messages(self, chat_id):
        """קבלת הודעות מטשאט ספציפי"""
        try:
            response = self.session.get(
                f"{self.base_url}/user/{self.userslug}/chats/{chat_id}",
                headers=self.headers
            )
            
            if response.ok:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                
                messages = []
                username = None
                content_lines = []
                
                # מעבר על כל השורות בטשאט
                chat_content = soup.select_one('.chat-content')
                if chat_content:
                    lines = [line.strip() for line in chat_content.text.split('\n') if line.strip()]
                    
                    for line in lines:
                        # התעלמות ממילים לסינון
                        if line in ['עריכה', 'מחיקה', 'שחזור', 'העתק טקסט', 'העתק קישור',
                                   'הצמד הודעה', 'בטל את הצמדת ההודעה', 'הצטרף לחדר']:
                            continue
                        
                        # אם זה שם משתמש חדש (מתחיל באות בודדת)
                        if len(line) == 1 and line in ['א', 'צ', 'ה', 'ש', 'ק', 'ב', 'ג', 'ד', 'ו', 'ז', 'ח', 'ט', 'י', 'כ', 'ל', 'מ', 'נ', 'ס', 'ע', 'פ', 'צ', 'ר', 'ת', 'S']:
                            # אם יש הודעה קודמת, נשמור אותה
                            if username and content_lines:
                                message_content = ' '.join(content_lines).strip()
                                if message_content and len(message_content) > 1:
                                    messages.append({
                                        'fromUser': {'username': username},
                                        'content': message_content
                                    })
                            # נתחיל הודעה חדשה
                            username = None
                            content_lines = []
                        # השורה שאחרי האות היא שם המשתמש
                        elif not username:
                            username = line
                        # כל שאר השורות הן תוכן ההודעה
                        else:
                            content_lines.append(line)
                
                # לא לשכוח את ההודעה האחרונה
                if username and content_lines:
                    message_content = ' '.join(content_lines).strip()
                    if message_content and len(message_content) > 1:
                        messages.append({
                            'fromUser': {'username': username},
                            'content': message_content
                        })
                
                # הפיכת סדר ההודעות
                #messages.reverse()
                
                print(f"נמצאו {len(messages)} הודעות בטשאט {chat_id}")
                
                # הדפסת ההודעות שנמצאו (רק לדיבוג)
                for msg in messages:
                    print(f"הודעה מ-{msg['fromUser']['username']}: {msg['content'][:100]}...")
                
                return messages
            
            return []
            
        except Exception as e:
            print(f"שגיאה בקבלת הודעות טשאט: {str(e)}")
            print("Stack trace:", traceback.format_exc())
            return []
        
    def get_chats(self):
        """קבלת כל הטשאטים של המשתמש וסידורם לפי מספר סידורי יורד"""
        try:
            print("מנסה לקבל רשימת טשאטים...")
            
            # קבלת דף הטשאטים הראשי
            response = self.session.get(
                f"{self.base_url}/chats",
                headers=self.headers
            )
            
            if response.ok:
                from bs4 import BeautifulSoup
                import re
                
                soup = BeautifulSoup(response.text, 'html.parser')
                chat_ids = set()  # שימוש בset למניעת כפילויות
                
                # חיפוש קישורים לטשאטים
                chat_links = soup.select('a[href*="/chats/"]')
                for link in chat_links:
                    href = link.get('href', '')
                    # חיפוש מספר הטשאט מתוך הקישור
                    match = re.search(r'/chats/(\d+)', href)
                    if match:
                        chat_ids.add(match.group(1))
                
                # חיפוש אלמנטים עם data-roomid
                room_elements = soup.select('[data-roomid]')
                for elem in room_elements:
                    room_id = elem.get('data-roomid')
                    if room_id and room_id.isdigit():
                        chat_ids.add(room_id)
                
                print(f"נמצאו {len(chat_ids)} מזהי טשאטים")
                
                # ממיינים את מזהי הטשאטים לפי מספר בסדר יורד
                sorted_chat_ids = sorted(chat_ids, key=lambda x: int(x), reverse=True)
                
                # קבלת מידע מפורט על כל טשאט
                chat_list = []
                for chat_id in sorted_chat_ids:
                    chat_data = self.get_chat_info(chat_id)
                    if chat_data:
                        chat_list.append(chat_data)
                        print(f"נוסף טשאט {chat_id}: {chat_data['roomName']}")
                
                if not chat_list:
                    # אם לא מצאנו טשאטים, ננסה דרך ה-API
                    print("מנסה לקבל טשאטים דרך ה-API...")
                    api_response = self.session.get(
                        f"{self.base_url}/api/v3/chats",
                        headers=self.headers
                    )
                    
                    if api_response.ok:
                        try:
                            data = api_response.json()
                            if isinstance(data, dict) and 'chats' in data:
                                # מיון הטשאטים מה-API לפי מספר סידורי יורד
                                api_chats = sorted(data['chats'], key=lambda x: int(x['roomId']), reverse=True)
                                
                                for chat in api_chats:
                                    chat_info = self.get_chat_info(str(chat['roomId']))
                                    if chat_info:
                                        chat_list.append(chat_info)
                                        print(f"נוסף טשאט {chat['roomId']}: {chat_info['roomName']}")
                        except Exception as e:
                            print(f"שגיאה בקבלת טשאטים מה-API: {str(e)}")
                
                print(f"נמצאו {len(chat_list)} טשאטים בסך הכל")
                return chat_list
                
            else:
                print(f"קוד תשובה לא תקין: {response.status_code}")
                return []
            
        except Exception as e:
            print(f"שגיאה בקבלת טשאטים: {str(e)}")
            return []

    def get_chat_info(self, chat_id):
        """קבלת מידע על טשאט ספציפי"""
        try:
            response = self.session.get(
                f"{self.base_url}/user/{self.userslug}/chats/{chat_id}",
                headers=self.headers
            )
            
            print(f"קוד תשובה לטשאט {chat_id}: {response.status_code}")
            
            if response.status_code == 404:
                print(f"טשאט {chat_id} לא נמצא")
                return None
            
            if response.ok:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # מציאת המשתתפים
                participants = set()
                user_elements = soup.select('[component="chat/message"] [component="user/username"], .username')
                
                for user in user_elements:
                    username = user.text.strip()
                    if username.endswith(':'):
                        username = username[:-1]  # הסרת הנקודותיים בסוף
                    if username and len(username) > 1:
                        participants.add(username)
                
                chat_data = {
                    'roomId': chat_id,
                    'users': [{'username': name} for name in participants],
                    'roomName': ', '.join(participants) if participants else f'צ\'אט {chat_id}'
                }
                
                print(f"נמצאו משתתפים בטשאט {chat_id}: {', '.join(participants)}")
                return chat_data
                
            return None
            
        except Exception as e:
            print(f"שגיאה בקבלת מידע על טשאט: {str(e)}")
            return None
        
class YemotAPI:
    def __init__(self, username, password):
        self.base_url = "https://www.call2all.co.il/ym/api/"
        self.username = username
        self.password = password
        self.token = None

    def login(self):
        try:
            response = requests.get(f"{self.base_url}Login", params={
                "username": self.username,
                "password": self.password
            })
            data = response.json()
            print("תגובת התחברות:", data)
            
            if data.get("responseStatus") == "OK":
                self.token = data.get("token")
                return True
            return False
        except Exception as e:
            print(f"שגיאה בהתחברות: {str(e)}")
            return False

        
    def parse_ymgr_file(self, extension_number):
        """פענוח קובץ ApprovalAll.ymgr"""
        if not self.token:
            print("נא להתחבר תחילה!")
            return None

        try:
            file_path = f"ivr2:{extension_number}/ApprovalAll.ymgr"
            print(f"מנסה לגשת לקובץ: {file_path}")
            
            params = {
                'token': self.token,
                'wath': file_path,
                'convertType': 'json',
                'notLoadLang': 0,
                'renderLanguage': 'HE'
            }
            
            response = requests.get(f"{self.base_url}RenderYMGRFile", params=params)
            data = response.json()
            
            if data.get("responseStatus") == "OK":
                result_data = data.get("data", [])
                print("\n=== נתוני אישורים ===")
                formatted_data = []
                
                for record in result_data:
                    if record.get('OrderState') == 'מאושר':  # רק רשומות מאושרות
                        formatted_record = {
                            'מצב הזמנה': record.get('OrderState', ''),
                            'שלוחה': record.get('Extension', ''),
                            'מערכת': record.get('System', ''),
                            'IncomingDID': record.get('IncomingDID', ''),
                            'טלפון': record.get('Phone', ''),
                            'תאריך': record.get('Date', ''),
                            'שעה': record.get('Time', ''),
                            'תאריך עברי': record.get('HebrewDate', ''),
                            'ערך/שלוחה': record.get('Value', ''),
                            'הזמנה': record.get('OrderNum', ''),
                            'PO50': record.get('PO50', ''),
                            'PO51': record.get('PO51', '')
                        }
                        formatted_data.append(formatted_record)
                        
                        print("\nרשומה:")
                        for key, value in formatted_record.items():
                            print(f"{key}: {value}")
                        print("-" * 50)
                
                return formatted_data
                
            return None
                
        except Exception as e:
            print(f"שגיאה בפענוח קובץ YMGR: {str(e)}")
            return None
    
    def upload_tts_file(self, extension, folder, filename, text):
        """העלאת קובץ TTS למערכת ימות"""
        try:
            # ניקוי הטקסט מתווים מיוחדים
            clean_text = self.clean_text_for_tts(text)
            
            # בניית הנתיב המלא
            full_path = f"ivr2:/5/{extension}/{folder}/{filename}.tts"
            
            # הכנת הנתונים לשליחה
            data = {
                "token": self.token,
                "what": full_path,
                "contents": clean_text,
                "encoding": "utf-8"  # הוספת קידוד מפורש
            }
            
            print(f"מעלה קובץ TTS: {full_path}")
            print(f"תוכן: {clean_text[:100]}..." if len(clean_text) > 100 else f"תוכן: {clean_text}")
            
            # שליחת הבקשה
            response = requests.post(
                f"{self.base_url}UploadTextFile",
                data=data,
                timeout=30  # הוספת timeout
            )
            
            # בדיקת התשובה
            if response.ok:
                try:
                    result = response.json()
                    if isinstance(result, dict):
                        if result.get('responseStatus') == 'OK':
                            print(f"קובץ TTS הועלה בהצלחה: {full_path}")
                            return True
                        else:
                            print(f"שגיאה בהעלאת קובץ TTS: {result.get('responseStatus')}")
                            print(f"תשובה מלאה: {result}")
                    else:
                        print(f"תשובה לא צפויה: {response.text}")
                except json.JSONDecodeError:
                    print(f"תשובה לא תקינה: {response.text}")
            else:
                print(f"שגיאת HTTP {response.status_code}: {response.text}")
            
            return False
            
        except Exception as e:
            print(f"שגיאה בהעלאת קובץ TTS: {str(e)}")
            return False        

def clean_text_for_tts(text):
    """מנקה טקסט להקראה"""
    # החלפת תווים מיוחדים
    text = text.replace('...', ' ')  # הסרת נקודות עוקבות
    text = text.replace('..', ' ')
    text = text.replace('/', ' ')    # החלפת קו נטוי ברווח
    text = text.replace('\\', ' ')   # החלפת קו נטוי הפוך ברווח
    text = text.replace('_', ' ')    # החלפת קו תחתון ברווח
    text = text.replace('`', '')     # הסרת גרש הפוך
    text = text.replace('"', '')     # הסרת מרכאות
    text = text.replace('\'', '')    # הסרת גרש
    text = text.replace('״', '')     # הסרת מרכאות עבריות
    text = text.replace('׳', '')     # הסרת גרש עברי
    text = text.replace('–', '-')    # החלפת מקף ארוך במקף רגיל
    text = text.replace('־', '-')    # החלפת מקף עברי במקף רגיל
    
    # הסרת תווים מיוחדים נוספים והחלפתם ברווח
    import re
    text = re.sub(r'[!@#$%^&*()=+\[\]{};:,<>?~]', ' ', text)
    
    # הסרת רווחים מיותרים
    text = ' '.join(text.split())
    
    return text

def clean_username(username):
    """מנקה את שם המשתמש מהמילים 'הצטרף לחדר'"""
    return username.replace(" הצטרף לחדר", "").strip()


def main():
    while True:  # לולאה אינסופית
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\nהתוכנית מתחילה... ({current_time})")
        api = YemotAPI("0747098744", "123456")
    
        if not api.login():
            print("ההתחברות לימות נכשלה")
            return

        print("התחברות לימות הצליחה!")

        # קריאת נתוני המשתמשים מקובץ YMGR
        print("מנסה לקרוא קובץ YMGR משלוחה 7...")
        file_path = "ivr2:7/ApprovalAll.ymgr"
        
        params = {
            'token': api.token,
            'wath': file_path,
            'convertType': 'json',
            'notLoadLang': 0,
            'renderLanguage': 'HE'
        }
        
        try:
            response = requests.get(f"{api.base_url}RenderYMGRFile", params=params)
            data = response.json()
            
            if data.get("responseStatus") == "OK":
                users_data = data.get("data", [])
                
                            # הדפסת הנתונים הגולמיים לדיבוג
                print("\nנתונים גולמיים שהתקבלו:")
                print(json.dumps(users_data, ensure_ascii=False, indent=2))
                # יצירת מילון משתמשים מהנתונים
                users = {}
                for record in users_data:
                    if record.get('מצב הזמנה') == 'מאושר':  # רק רשומות מאושרות
                        username = record.get('P050', '').strip()
                        password = record.get('P051', '').strip()
                        
                        if username and password:
                            sub_extension = len(users) + 1
                            users[username] = {
                                "forum_username": username,
                                "forum_password": password,
                                "sub_extension": sub_extension
                            }
                            print(f"נוסף משתמש: {username} עם שלוחה {sub_extension}")

                if not users:
                    print("לא נמצאו משתמשים מאושרים")
                    return

                print(f"\nנמצאו {len(users)} משתמשים")

                # טיפול בכל המשתמשים
                for username, user_data in users.items():
                    print(f"\nמטפל במשתמש: {username}")
                    
                    nodebb = NodeBBAPI()
                    if nodebb.login(user_data['forum_username'], user_data['forum_password']):
                        print(f"התחברות לפורום הצליחה עבור {username}!")
                        
                        # קבלת הטשאטים של המשתמש
                        chats = nodebb.get_chats()
                        sorted_chats = sorted(chats, key=lambda x: int(x['roomId']), reverse=True)
                        
                        # יצירת אינדקס לטשאטים של המשתמש
                        chat_index_text = "ברוכים הבאים למערכת הטשאטים.\n"
                        chat_details = []
                        
                        # עיבוד הטשאטים
                        for chat_index, chat in enumerate(sorted_chats, 1):
                            messages = nodebb.get_chat_messages(chat['roomId'])
                            
                            if not messages:
                                continue

                            # מציאת המשתמש השני בטשאט
                            other_user = None
                            for message in messages:
                                username_in_chat = clean_username(message['fromUser']['username'])
                                if username_in_chat != user_data['forum_username']:
                                    other_user = username_in_chat
                                    break
                            
                            if not other_user:
                                continue

                            print(f"נמצא טשאט {chat_index} עם {other_user}")
                            chat_index_text += f"לטשאט עם {other_user}, אנא הקש {chat_index}.\n"
                            chat_details.append({
                                'index': chat_index,
                                'username': other_user,
                                'messages': messages,
                                'roomId': chat['roomId']
                            })

                        # העלאת האינדקס לשלוחה של המשתמש
                        print(f"\nמעלה אינדקס לשלוחה 5/{user_data['sub_extension']}...")
                        data = {
                            "token": api.token,
                            "what": f"ivr2:/5/{user_data['sub_extension']}/M1000.tts",
                            "contents": clean_text_for_tts(chat_index_text)
                        }
                        try:
                            response = requests.post(f"{api.base_url}UploadTextFile", data=data)
                            if response.status_code == 200 and response.json().get('responseStatus') == 'OK':
                                print(f"אינדקס טשאטים הועלה בהצלחה למשתמש {username}")
                                print(f"תוכן האינדקס:\n{chat_index_text}")
                        except Exception as e:
                            print(f"שגיאה בהעלאת אינדקס: {str(e)}")

                        # העלאת תוכן הטשאטים
                        for chat in chat_details:
                            print(f"\nמעלה טשאט {chat['index']} למשתמש {username}...")
                            
                            # העלאת הקדמת הטשאט
                            chat_intro = f"טשאט עם {chat['username']}. {len(chat['messages'])} הודעות. מזהה חדר {chat['roomId']}"
                            data = {
                                "token": api.token,
                                "what": f"ivr2:/5/{user_data['sub_extension']}/{chat['index']}/000.tts",
                                "contents": clean_text_for_tts(chat_intro)
                            }
                            try:
                                response = requests.post(f"{api.base_url}UploadTextFile", data=data)
                                if response.status_code == 200:
                                    print(f"הקדמת טשאט {chat['index']} הועלתה")
                            except Exception as e:
                                print(f"שגיאה בהעלאת הקדמה: {str(e)}")

                            # העלאת ההודעות
                            for msg_index, message in enumerate(chat['messages'], 1):
                                username = clean_username(message['fromUser']['username'])
                                msg_text = f"הודעה מ{username}: {message['content']}"
                                data = {
                                    "token": api.token,
                                    "what": f"ivr2:/5/{user_data['sub_extension']}/{chat['index']}/{msg_index:03d}.tts",
                                    "contents": clean_text_for_tts(msg_text)
                                }
                                try:
                                    response = requests.post(f"{api.base_url}UploadTextFile", data=data)
                                    if response.status_code == 200:
                                        print(f"הודעה {msg_index} הועלתה")
                                except Exception as e:
                                    print(f"שגיאה בהעלאת הודעה: {str(e)}")
                                
                                time.sleep(0.1)
                            
                            time.sleep(0.5)
                    else:
                        print(f"ההתחברות לפורום נכשלה עבור {username}")
            else:
                print("שגיאה בקריאת קובץ YMGR")
                return
                
        except Exception as e:
            print(f"שגיאה בקריאת קובץ YMGR: {str(e)}")
            return

        print("התוכנית הסתיימה")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nהתוכנית הופסקה ידנית על ידי המשתמש")
    except Exception as e:
        print(f"\nשגיאה לא צפויה: {str(e)}")
