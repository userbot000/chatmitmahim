"""
סקריפט בדיקה - מראה מה יקרה בלי לשלוח הודעות בפועל
"""
import requests
import urllib3
from bs4 import BeautifulSoup
from datetime import datetime
import json
import os

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class NodeBBTestMode:
    def __init__(self, username, password):
        self.session = requests.Session()
        self.session.verify = False
        self.base_url = "https://mitmachim.top"
        self.username = username
        self.password = password
        self.userslug = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }

    def login(self):
        """התחברות לפורום"""
        try:
            print(f"🔐 מתחבר לפורום בתור '{self.username}'...")
            
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
                    print(f"   🔑 קיבלתי CSRF token")
            
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
                    
                    print(f"✅ התחברות הצליחה! userslug: {self.userslug}\n")
                    return True
            
            print(f"❌ התחברות נכשלה - קוד: {login_response.status_code}")
            print(f"   תגובה: {login_response.text[:200]}\n")
            return False
            
        except Exception as e:
            print(f"❌ שגיאה בהתחברות: {str(e)}\n")
            return False

    def get_chats(self):
        """קבלת רשימת כל הצ'אטים"""
        try:
            print("📋 מקבל רשימת צ'אטים...")
            
            response = self.session.get(
                f"{self.base_url}/chats",
                headers=self.headers
            )
            
            if response.ok:
                soup = BeautifulSoup(response.text, 'html.parser')
                chat_ids = set()
                
                import re
                chat_links = soup.select('a[href*="/chats/"]')
                for link in chat_links:
                    href = link.get('href', '')
                    match = re.search(r'/chats/(\d+)', href)
                    if match:
                        chat_ids.add(match.group(1))
                
                room_elements = soup.select('[data-roomid]')
                for elem in room_elements:
                    room_id = elem.get('data-roomid')
                    if room_id and room_id.isdigit():
                        chat_ids.add(room_id)
                
                sorted_chats = sorted(chat_ids, key=lambda x: int(x), reverse=True)
                print(f"✅ נמצאו {len(sorted_chats)} צ'אטים\n")
                return sorted_chats
                
            print(f"❌ שגיאה בקבלת צ'אטים - קוד: {response.status_code}\n")
            return []
            
        except Exception as e:
            print(f"❌ שגיאה בקבלת צ'אטים: {str(e)}\n")
            return []

    def get_chat_messages(self, chat_id):
        """קבלת כל ההודעות בצ'אט (ללא הודעות מערכת)"""
        try:
            response = self.session.get(
                f"{self.base_url}/user/{self.userslug}/chats/{chat_id}",
                headers=self.headers
            )
            
            if response.ok:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                messages = []
                chat_content = soup.select_one('.chat-content')
                if chat_content:
                    lines = [line.strip() for line in chat_content.text.split('\n') if line.strip()]
                    
                    username = None
                    content_lines = []
                    
                    for line in lines:
                        # דילוג על כפתורים ופעולות
                        if line in ['עריכה', 'מחיקה', 'שחזור', 'העתק טקסט', 'העתק קישור',
                                   'הצמד הודעה', 'בטל את הצמדת ההודעה']:
                            continue
                        
                        # דילוג על הודעות מערכת
                        if 'הצטרף לחדר' in line or 'joined the room' in line.lower():
                            continue
                        
                        if len(line) == 1:
                            if username and content_lines:
                                message_content = ' '.join(content_lines).strip()
                                # סינון הודעות מערכת נוספות
                                if (message_content and 
                                    len(message_content) > 1 and 
                                    'הצטרף לחדר' not in message_content and
                                    'joined the room' not in message_content.lower()):
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
                        # סינון הודעות מערכת נוספות
                        if (message_content and 
                            len(message_content) > 1 and 
                            'הצטרף לחדר' not in message_content and
                            'joined the room' not in message_content.lower()):
                            messages.append({
                                'username': username,
                                'content': message_content
                            })
                
                return messages  # מחזיר רק הודעות אמיתיות ממשתמשים
            
            return []
            
        except Exception as e:
            print(f"   ⚠️  שגיאה בקריאת צ'אט {chat_id}: {str(e)}")
            return None

    def test_auto_reply(self, auto_reply_message):
        """בדיקת מה יקרה בלי לשלוח הודעות בפועל"""
        chat_ids = self.get_chats()
        
        # טעינת רשימת צ'אטים שכבר טופלו
        replied_chats_file = f"replied_chats_{self.username}.json"
        replied_chats = {}
        if os.path.exists(replied_chats_file):
            try:
                with open(replied_chats_file, 'r', encoding='utf-8') as f:
                    replied_chats = json.load(f)
                print(f"📂 נטען קובץ היסטוריה עם {len(replied_chats)} צ'אטים שכבר טופלו\n")
            except:
                pass
        
        print("=" * 70)
        print("🔍 בודק צ'אטים - מצב סימולציה (לא שולח הודעות בפועל)")
        print("=" * 70)
        print()
        
        would_reply = []
        would_skip = []
        
        for i, chat_id in enumerate(chat_ids, 1):
            print(f"[{i}/{len(chat_ids)}] צ'אט #{chat_id}")
            
            # *** בדיקה קשוחה 1: האם כבר השבנו לצ'אט הזה? ***
            if chat_id in replied_chats:
                prev_reply = replied_chats[chat_id]
                print(f"   🛑 כבר טופל ב-{prev_reply.get('timestamp', 'לא ידוע')}")
                print(f"   🛑 מדלג - לעולם לא נשלח שוב לצ'אט זה!")
                print(f"   📝 הודעה מקורית: {prev_reply.get('message_preview', '')[:50]}...")
                would_skip.append({
                    'chat_id': chat_id,
                    'reason': 'כבר טופל בעבר'
                })
                print()
                continue
            
            # קבלת כל ההודעות בצ'אט
            messages = self.get_chat_messages(chat_id)
            
            if not messages:
                print(f"   ⚠️  לא נמצאו הודעות בצ'אט")
                would_skip.append({
                    'chat_id': chat_id,
                    'reason': 'אין הודעות'
                })
                print()
                continue
            
            print(f"   📊 מספר הודעות: {len(messages)}")
            
            # בדיקה: רק אם יש בדיוק 2 הודעות
            if len(messages) != 2:
                print(f"   ⏭️  מדלג - יש {len(messages)} הודעות (צריך בדיוק 2)")
                would_skip.append({
                    'chat_id': chat_id,
                    'reason': f'יש {len(messages)} הודעות (צריך 2)'
                })
                print()
                continue
            
            # בדיקת שתי ההודעות
            first_message = messages[0]
            second_message = messages[1]
            
            first_sender = first_message['username']
            second_sender = second_message['username']
            first_content = first_message['content']
            second_content = second_message['content']
            
            print(f"   👤 הודעה 1 מ-{first_sender}: {first_content[:60]}...")
            print(f"   👤 הודעה 2 מ-{second_sender}: {second_content[:60]}...")
            
            # *** בדיקה קשוחה 2: האם אחת מההודעות היא התגובה האוטומטית? ***
            if (auto_reply_message in first_content or 
                auto_reply_message in second_content):
                print(f"   🛑 נמצאה התגובה האוטומטית בצ'אט - כבר נשלחה!")
                print(f"   🛑 מדלג למניעת שליחה כפולה")
                would_skip.append({
                    'chat_id': chat_id,
                    'reason': 'נמצאה תגובה אוטומטית קיימת'
                })
                print()
                continue
            
            # *** בדיקה קשוחה 3: האם יש הודעה ממך בצ'אט? ***
            has_my_message = False
            for msg in messages:
                if msg['username'] == self.username:
                    has_my_message = True
                    print(f"   🛑 נמצאה הודעה ממך בצ'אט - כבר השבת!")
                    break
            
            if has_my_message:
                print(f"   🛑 מדלג למניעת שליחה כפולה")
                would_skip.append({
                    'chat_id': chat_id,
                    'reason': 'נמצאה הודעה ממך'
                })
                print()
                continue
            
            # אם הגענו לכאן - בטוח שלא שלחנו הודעה
            print(f"   ✅ צ'אט תקין - יישלח: '{auto_reply_message}'")
            would_reply.append({
                'chat_id': chat_id,
                'sender': second_sender,
                'message_preview': second_content[:100]
            })
            
            print()
        
        # סיכום
        print("=" * 70)
        print("📊 סיכום")
        print("=" * 70)
        print(f"✅ צ'אטים שיקבלו תגובה: {len(would_reply)}")
        print(f"⏭️  צ'אטים שידלגו: {len(would_skip)}")
        print()
        
        if would_reply:
            print("📤 צ'אטים שיקבלו תגובה אוטומטית:")
            for item in would_reply:
                print(f"   • צ'אט #{item['chat_id']} מ-{item['sender']}")
                print(f"     הודעה: {item['message_preview'][:60]}...")
            print()
        
        if would_skip:
            print("⏭️  צ'אטים שידלגו:")
            skip_reasons = {}
            for item in would_skip:
                reason = item['reason']
                skip_reasons[reason] = skip_reasons.get(reason, 0) + 1
            
            for reason, count in skip_reasons.items():
                print(f"   • {reason}: {count} צ'אטים")
            print()
        
        print("=" * 70)
        print(f"⏰ בדיקה הסתיימה ב-{datetime.now().strftime('%H:%M:%S')}")
        print("=" * 70)

def main():
    print("=" * 70)
    print("🧪 מצב בדיקה - Auto Reply Test")
    print("=" * 70)
    print()
    
    # פרטי התחברות
    username = "הבל-הבלים"
    password = "pwM9tDN4Y@uV9"
    auto_reply = "תודה על ההודעה! אני אחזור אליך בהקדם האפשרי."
    
    print(f"👤 משתמש: {username}")
    print(f"💬 תגובה אוטומטית: '{auto_reply}'")
    print()
    
    tester = NodeBBTestMode(username, password)
    
    if tester.login():
        tester.test_auto_reply(auto_reply)
    else:
        print("❌ לא ניתן להמשיך - ההתחברות נכשלה")
        print("\n💡 טיפים:")
        print("   • בדוק ששם המשתמש והסיסמה נכונים")
        print("   • נסה להתחבר ידנית לפורום כדי לוודא שהחשבון פעיל")
        print("   • אם שם המשתמש הוא 'הבל-הבלים', נסה גם '@הבל-הבלים'")

if __name__ == "__main__":
    main()
