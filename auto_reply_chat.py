import requests
import urllib3
from bs4 import BeautifulSoup
from datetime import datetime
import time
import json
import os

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class NodeBBAutoReply:
    def __init__(self, username, password, auto_reply_message):
        self.session = requests.Session()
        self.session.verify = False
        self.base_url = "https://mitmachim.top"
        self.username = username
        self.password = password
        self.auto_reply_message = auto_reply_message
        self.userslug = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        # קובץ לשמירת מזהי צ'אטים שכבר קיבלו תגובה
        self.replied_chats_file = f"replied_chats_{username}.json"
        self.replied_chats = self.load_replied_chats()

    def load_replied_chats(self):
        """טוען את רשימת הצ'אטים שכבר קיבלו תגובה"""
        try:
            if os.path.exists(self.replied_chats_file):
                with open(self.replied_chats_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"שגיאה בטעינת קובץ צ'אטים: {str(e)}")
        return {}

    def save_replied_chats(self):
        """שומר את רשימת הצ'אטים שכבר קיבלו תגובה"""
        try:
            with open(self.replied_chats_file, 'w', encoding='utf-8') as f:
                json.dump(self.replied_chats, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"שגיאה בשמירת קובץ צ'אטים: {str(e)}")

    def login(self):
        """התחברות לפורום"""
        try:
            print(f"מתחבר לפורום בתור {self.username}...")
            
            # קודם מקבלים CSRF token
            config_response = self.session.get(
                f"{self.base_url}/api/config",
                headers=self.headers
            )
            
            if config_response.ok:
                config_data = config_response.json()
                csrf_token = config_data.get('csrf_token')
                if csrf_token:
                    self.headers['X-CSRF-Token'] = csrf_token
                    print(f"קיבלתי CSRF token")
            
            login_data = {
                "username": self.username,
                "password": self.password
            }
            
            login_response = self.session.post(
                f"{self.base_url}/api/v3/utilities/login",
                json=login_data,
                headers=self.headers
            )
            
            if login_response.ok:
                response_data = login_response.json()
                if response_data.get('status', {}).get('code') == 'ok':
                    user_data = response_data.get('response', {})
                    self.userslug = user_data.get('userslug')
                    self.session.cookies.update(login_response.cookies)
                    
                    # עדכון CSRF token אחרי התחברות
                    config_response2 = self.session.get(
                        f"{self.base_url}/api/config",
                        headers=self.headers
                    )
                    if config_response2.ok:
                        config_data2 = config_response2.json()
                        csrf_token2 = config_data2.get('csrf_token')
                        if csrf_token2:
                            self.headers['X-CSRF-Token'] = csrf_token2
                    
                    print(f"התחברות הצליחה! userslug: {self.userslug}")
                    return True
                    
            print("התחברות נכשלה")
            return False
            
        except Exception as e:
            print(f"שגיאה בהתחברות: {str(e)}")
            return False

    def get_chats(self):
        """קבלת רשימת כל הצ'אטים"""
        try:
            print("מקבל רשימת צ'אטים...")
            
            response = self.session.get(
                f"{self.base_url}/chats",
                headers=self.headers
            )
            
            if response.ok:
                soup = BeautifulSoup(response.text, 'html.parser')
                chat_ids = set()
                
                # חיפוש קישורים לצ'אטים
                import re
                chat_links = soup.select('a[href*="/chats/"]')
                for link in chat_links:
                    href = link.get('href', '')
                    match = re.search(r'/chats/(\d+)', href)
                    if match:
                        chat_ids.add(match.group(1))
                
                # חיפוש אלמנטים עם data-roomid
                room_elements = soup.select('[data-roomid]')
                for elem in room_elements:
                    room_id = elem.get('data-roomid')
                    if room_id and room_id.isdigit():
                        chat_ids.add(room_id)
                
                print(f"נמצאו {len(chat_ids)} צ'אטים")
                return sorted(chat_ids, key=lambda x: int(x), reverse=True)
                
            return []
            
        except Exception as e:
            print(f"שגיאה בקבלת צ'אטים: {str(e)}")
            return []

    def get_last_message(self, chat_id):
        """קבלת ההודעה האחרונה בצ'אט"""
        try:
            response = self.session.get(
                f"{self.base_url}/user/{self.userslug}/chats/{chat_id}",
                headers=self.headers
            )
            
            if response.ok:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # מציאת כל ההודעות
                messages = []
                chat_content = soup.select_one('.chat-content')
                if chat_content:
                    lines = [line.strip() for line in chat_content.text.split('\n') if line.strip()]
                    
                    username = None
                    content_lines = []
                    
                    for line in lines:
                        if line in ['עריכה', 'מחיקה', 'שחזור', 'העתק טקסט', 'העתק קישור',
                                   'הצמד הודעה', 'בטל את הצמדת ההודעה', 'הצטרף לחדר']:
                            continue
                        
                        if len(line) == 1:
                            if username and content_lines:
                                message_content = ' '.join(content_lines).strip()
                                if message_content and len(message_content) > 1:
                                    messages.append({
                                        'username': username,
                                        'content': message_content
                                    })
                            username = None
                            content_lines = []
                        elif not username:
                            username = line
                        else:
                            content_lines.append(line)
                    
                    if username and content_lines:
                        message_content = ' '.join(content_lines).strip()
                        if message_content and len(message_content) > 1:
                            messages.append({
                                'username': username,
                                'content': message_content
                            })
                
                if messages:
                    return messages[-1]  # ההודעה האחרונה
            
            return None
            
        except Exception as e:
            print(f"שגיאה בקבלת הודעות מצ'אט {chat_id}: {str(e)}")
            return None

    def send_message(self, chat_id, message):
        """שליחת הודעה לצ'אט"""
        try:
            # נסיון ראשון - דרך API v3
            response = self.session.post(
                f"{self.base_url}/api/v3/chats/{chat_id}",
                json={"message": message},
                headers=self.headers
            )
            
            if response.ok:
                print(f"הודעה נשלחה בהצלחה לצ'אט {chat_id}")
                return True
            
            # אם נכשל, ננסה דרך API רגיל
            print(f"נסיון ראשון נכשל ({response.status_code}), מנסה דרך חלופית...")
            
            response2 = self.session.post(
                f"{self.base_url}/api/chats/{chat_id}",
                json={"message": message},
                headers=self.headers
            )
            
            if response2.ok:
                print(f"הודעה נשלחה בהצלחה לצ'אט {chat_id} (דרך חלופית)")
                return True
            
            print(f"שגיאה בשליחת הודעה: {response.status_code} / {response2.status_code}")
            print(f"תגובה 1: {response.text[:200]}")
            print(f"תגובה 2: {response2.text[:200]}")
            return False
                
        except Exception as e:
            print(f"שגיאה בשליחת הודעה: {str(e)}")
            return False

    def process_chats(self):
        """עיבוד כל הצ'אטים ושליחת תגובות אוטומטיות"""
        chat_ids = self.get_chats()
        
        new_replies = 0
        for chat_id in chat_ids:
            print(f"\nבודק צ'אט {chat_id}...")
            
            # בדיקה אם כבר השבנו לצ'אט הזה
            if chat_id in self.replied_chats:
                print(f"צ'אט {chat_id} כבר קיבל תגובה בעבר")
                continue
            
            # קבלת ההודעה האחרונה
            last_message = self.get_last_message(chat_id)
            
            if last_message:
                sender = last_message['username']
                content = last_message['content']
                
                print(f"הודעה אחרונה מ-{sender}: {content[:50]}...")
                
                # אם ההודעה האחרונה לא ממני, שולחים תגובה אוטומטית
                if sender != self.username:
                    print(f"שולח תגובה אוטומטית לצ'אט {chat_id}...")
                    
                    if self.send_message(chat_id, self.auto_reply_message):
                        # שמירת הצ'אט כמי שכבר קיבל תגובה
                        self.replied_chats[chat_id] = {
                            'timestamp': datetime.now().isoformat(),
                            'sender': sender,
                            'message_preview': content[:100]
                        }
                        self.save_replied_chats()
                        new_replies += 1
                        time.sleep(2)  # המתנה בין הודעות
                else:
                    print(f"ההודעה האחרונה היא ממני, מדלג...")
            
            time.sleep(1)  # המתנה בין צ'אטים
        
        return new_replies

def main():
    # הגדרת פרטי התחברות - ערוך את הערכים כאן
    username = "הבל-הבלים"  # שם המשתמש שלך בפורום
    password = "pwM9tDN4Y@uV9"  # הסיסמה שלך בפורום
    auto_reply = "תודה על ההודעה! אני אחזור אליך בהקדם האפשרי."  # התגובה האוטומטית
    
    if not username or username == "YOUR_USERNAME":
        print("שגיאה: יש לערוך את שם המשתמש והסיסמה בקוד")
        return
    
    print(f"=== התחלת ריצה: {datetime.now()} ===")
    print(f"משתמש: {username}")
    print(f"תגובה אוטומטית: {auto_reply}")
    
    bot = NodeBBAutoReply(username, password, auto_reply)
    
    if bot.login():
        new_replies = bot.process_chats()
        print(f"\n=== סיום ריצה: {datetime.now()} ===")
        print(f"נשלחו {new_replies} תגובות חדשות")
    else:
        print("ההתחברות נכשלה")

if __name__ == "__main__":
    main()
