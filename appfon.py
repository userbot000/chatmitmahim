import requests
from bs4 import BeautifulSoup
import json
import time
import urllib3
import re
from datetime import datetime
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def my_where():
    return r'C:\ProgramData\NetFree\CA\netfree-ca-list.crt'
requests.certs.where = my_where


# מחלקה לתקשורת עם ימות

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


            
    def upload_profile_tts(self, text):
        """
        מעלה קובץ TTS עם נתוני הפרופיל
        """
        if not self.token:
            print("נדרשת התחברות תחילה")
            return False

        clean_text = re.sub(r'https?://\S+', '', text)  # ניקוי קישורים
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()  # ניקוי רווחים מיותרים

        if not clean_text:
            print("אין טקסט להקראה")
            return False

        data = {
            "token": self.token,
            "what": "ivr2:/3/000.tts",  # שם קובץ קבוע לפרופיל
            "contents": clean_text
        }

        try:
            print("מעלה נתוני פרופיל...")
            print(f"תוכן הפרופיל: {clean_text}")
            
            response = requests.post(f"{self.base_url}UploadTextFile", data=data)
            
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get('responseStatus') == 'OK':
                    print("נתוני הפרופיל הועלו בהצלחה")
                    return True
                else:
                    print(f"שגיאה בתגובת השרת: {response_data}")
                    return False
            else:
                print(f"שגיאה בהעלאת נתוני הפרופיל: {response.status_code}")
                print(f"תוכן התגובה: {response.text}")
                return False
                
        except Exception as e:
            print(f"שגיאה בהעלאת נתוני הפרופיל: {str(e)}")
            return False

    def upload_tts_file(self, text, index):
        if not self.token:
            print("נדרשת התחברות תחילה")
            return False

        # שימוש בפונקציה המשופרת לניקוי טקסט
        clean_text = clean_text_for_tts(text, index + 1)  # index + 1 כדי שההתראות יתחילו מ-1

        if not clean_text:
            print("אין טקסט להקראה אחרי הניקוי")
            return False

        # יצירת שם קובץ עם המספר הסידורי
        file_name = f"{index:03d}.tts"  # למשל: 000.tts, 001.tts, 002.tts
        
        data = {
            "token": self.token,
            "what": f"ivr2:/1/{file_name}",
            "contents": clean_text
        }

        try:
            print(f"\nמעלה התראה מספר {index + 1}:")
            print(f"שם הקובץ: {file_name}")
            print(f"תוכן ההתראה: {clean_text}")
            
            response = requests.post(f"{self.base_url}UploadTextFile", data=data)
            
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get('responseStatus') == 'OK':
                    print(f"התראה {index + 1} הועלתה בהצלחה")
                    return True
                else:
                    print(f"שגיאה בתגובת השרת: {response_data}")
                    return False
            else:
                print(f"שגיאה בהעלאת התראה {index + 1}: {response.status_code}")
                print(f"תוכן התגובה: {response.text}")
                return False
                
        except Exception as e:
            print(f"שגיאה בהעלאת התראה {index + 1}: {str(e)}")
            return False
    
def clean_text_for_tts(text, notification_number=None):
    """
    מנקה ומעבד טקסט להקראה עם שיפורים
    """
    # רק אם יש מספר התראה, נוסיף את הפתיח
    if notification_number is not None:
        text = f"התראה מספר {notification_number}. {text}"
    
    # ניקוי קישורים והחלפתם במילה [קישור]
    text = re.sub(r'https?://\S+', '[קישור]', text)
    
    # ניקוי תמונות והחלפתם במילה [תמונה]
    text = re.sub(r'!\[.*?\]\(.*?\)', '[תמונה]', text)
    
    # ניקוי סיומות קבצים
    text = re.sub(r'\.txt|\.exe|\.rar|\.zip|\.py', '', text)
    
    # ניקוי תווים לא רצויים אבל שמירה על עברית ואנגלית
    text = re.sub(r'[^\u0590-\u05FF\u0020-\u007F\s\.\,\?\!]', '', text)
    
    # הסרת רווחים מיותרים
    text = re.sub(r'\s+', ' ', text).strip()
    
    # טיפול בציטוטים
    text = re.sub(r'> ?', 'ציטוט: ', text)
    
    # הוספת נקודה בסוף אם אין
    if not text.endswith(('.', '!', '?')):
        text += '.'
    
    return text

def get_nodebb_post_content(url):
    """
    מושך תוכן מפוסט של NodeBB באמצעות ה-API
    """
    try:
        username = url.split('/')[-1]
        api_url = f"https://mitmachim.top/api/user/{username}/posts"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        }
        
        response = requests.get(api_url, verify=False, headers=headers)
        data = response.json()
        
        if 'posts' in data:
            all_content = []
            for post in data['posts']:
                if 'content' in post:
                    soup = BeautifulSoup(post['content'], 'html.parser')
                    text = soup.get_text(strip=True)
                    clean_text = clean_text_for_tts(text)
                    if clean_text:
                        all_content.append(clean_text)
            
            return ' '.join(all_content)
        else:
            print("לא נמצא תוכן בתגובת ה-API")
            return None
            
    except Exception as e:
        print(f"שגיאה בקריאת תוכן מ-NodeBB: {str(e)}")
        return None

def split_text_to_chunks(text, max_length=150):
    """
    מחלק טקסט לחלקים קטנים
    """
    sentences = text.split('.')
    chunks = []
    current_chunk = []
    current_length = 0

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        if current_length + len(sentence) + 2 <= max_length:
            current_chunk.append(sentence)
            current_length += len(sentence) + 2
        else:
            if current_chunk:
                chunks.append('. '.join(current_chunk) + '.')
            current_chunk = [sentence]
            current_length = len(sentence)

    if current_chunk:
        chunks.append('. '.join(current_chunk) + '.')

    return chunks




class NodeBBAPI:
    def __init__(self):
        self.session = requests.Session()
        self.session.verify = False
        self.base_url = "https://mitmachim.top"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': 'https://mitmachim.top',
            'Referer': 'https://mitmachim.top/'
        }
        self.user_data = None

    def login(self, username, password):
        try:
            print("מתחיל תהליך התחברות ישיר דרך ה-API...")
            
            # קבלת config
            config_response = self.session.get(
                f"{self.base_url}/api/config",
                headers=self.headers
            )
            print(f"תגובת config: {config_response.status_code}")
            if config_response.ok:
                config_data = config_response.json()
                print(f"מידע מה-config: {json.dumps(config_data, ensure_ascii=False)[:200]}")
            
            # התחברות
            login_data = {
                "username": username,
                "password": password
            }
            
            print("שולח בקשת התחברות...")
            login_response = self.session.post(
                f"{self.base_url}/api/v3/utilities/login",
                json=login_data,
                headers=self.headers
            )
            
            print(f"קוד תשובה: {login_response.status_code}")
            if login_response.ok:
                response_data = login_response.json()
                print(f"תוכן תגובה: {json.dumps(response_data, ensure_ascii=False)}")
                
                if response_data.get('status', {}).get('code') == 'ok':
                    self.user_data = response_data.get('response', {})
                    print("התחברות הצליחה!")
                    return True

            print("התחברות נכשלה")
            return False
            
        except Exception as e:
            print(f"שגיאה בהתחברות: {str(e)}")
            return False

    def get_notifications(self):
        if not self.user_data:
            print("יש להתחבר תחילה!")
            return None

        try:
            print("מנסה לקבל התראות...")
            
            response = self.session.get(
                f"{self.base_url}/api/notifications",
                headers=self.headers
            )
            
            if response.ok:
                data = response.json()
                if isinstance(data, dict) and 'notifications' in data:
                    notifications = data['notifications']
                elif isinstance(data, list):
                    notifications = data
                else:
                    notifications = []

                print(f"נמצאו {len(notifications)} התראות")
                
                # עיבוד ההתראות לטקסט
                all_content = []
                for notif in notifications:
                    # קבלת שם המשתמש
                    username = notif.get('user', {}).get('username', 'משתמש לא ידוע')
                    notification_type = notif.get('type', '')
                    
                    # קבלת הטקסט של ההתראה והפוסט
                    notification_content = ""
                    post_content = ""
                    
                    # קבלת תוכן ההתראה הקצר (bodyShort)
                    if 'bodyShort' in notif and notif['bodyShort']:
                        notification_content = BeautifulSoup(notif['bodyShort'], 'html.parser').get_text(strip=True)
                    
                    # קבלת תוכן הפוסט המלא (bodyLong)
                    if 'bodyLong' in notif and notif['bodyLong']:
                        post_content = BeautifulSoup(notif['bodyLong'], 'html.parser').get_text(strip=True)
                    
                    # בניית הודעה מותאמת לפי סוג ההתראה
                    notification_text = ""
                    if notification_type == 'upvote':
                        notification_text = f"@{username} הצביע בעד הפוסט שלך"
                    elif notification_type == 'new_reply':
                        notification_text = f"@{username} הגיב לפוסט שלך"
                    elif notification_type == 'follow':
                        notification_text = f"@{username} התחיל לעקוב אחריך"
                    elif notification_type == 'mention':
                        notification_text = f"@{username} הזכיר אותך"
                    elif notification_type == 'quote':
                        notification_text = f"@{username} ציטט את דבריך"
                    elif notification_type == 'new_chat':
                        notification_text = f"@{username} שלח לך הודעה פרטית"
                    elif notification_type == 'group_invite':
                        notification_text = f"@{username} הזמין אותך להצטרף לקבוצה"
                    else:
                        notification_text = notification_content
                    
                    # הוספת תוכן ההודעה אם קיים
                    final_text = notification_text
                    if notification_content and notification_content not in notification_text:
                        final_text += f". תוכן ההתראה: {notification_content}"
                    if post_content and post_content not in final_text:
                        final_text += f". תוכן הפוסט: {post_content}"
                    
                    if final_text:
                        all_content.append(final_text)
                
                if all_content:
                    return all_content
                else:
                    print("לא נמצא טקסט בהתראות")
                    return None
            else:
                print(f"שגיאה בקבלת התראות: {response.status_code}")
                print(f"תוכן התגובה: {response.text[:200]}")
                return None
                
        except Exception as e:
            print(f"שגיאה בקבלת התראות: {str(e)}")
            return None
    def get_user_profile(self, username=None):
        """
        מושך את נתוני הפרופיל של משתמש
        """
        if not self.user_data:
            print("יש להתחבר תחילה!")
            return None

        try:
            print(f"מושך נתוני פרופיל עבור המשתמש: {username}")
            
            # החלפת רווחים במקפים ואז קידוד URL
            from urllib.parse import quote
            formatted_username = username.replace(" ", "-")
            encoded_username = quote(formatted_username)
            
            # שימוש בנתיב הנכון
            response = self.session.get(
                f"{self.base_url}/api/user/{encoded_username}",
                headers=self.headers
            )
            
            print(f"קוד תגובה מהשרת: {response.status_code}")
            print(f"URL שנוסה: {response.url}")
            
            if response.ok:
                data = response.json()
                print(f"התקבלו נתונים: {json.dumps(data, ensure_ascii=False)[:200]}")
                
                # בניית טקסט מובנה מנתוני הפרופיל
                profile_parts = []
                
                # שם המשתמש
                username_display = data.get('username', username)
                profile_parts.append(f"פרופיל המשתמש {username_display}")
                
                # תיאור/חתימה
                if 'aboutme' in data and data['aboutme']:
                    aboutme = BeautifulSoup(data['aboutme'], 'html.parser').get_text(strip=True)
                    if aboutme:
                        profile_parts.append(f"אודות: {aboutme}")
                
                if 'signature' in data and data['signature']:
                    signature = BeautifulSoup(data['signature'], 'html.parser').get_text(strip=True)
                    if signature:
                        profile_parts.append(f"חתימה: {signature}")
                
                # מיקום
                if 'location' in data and data['location']:
                    profile_parts.append(f"מיקום: {data['location']}")
                
                # תאריך הצטרפות
                if 'joindate' in data:
                    from datetime import datetime
                    join_date = datetime.fromtimestamp(int(data['joindate'])/1000).strftime('%d/%m/%Y')
                    profile_parts.append(f"הצטרף בתאריך: {join_date}")
                
                # סטטיסטיקות
                if 'postcount' in data:
                    profile_parts.append(f"מספר פוסטים: {data['postcount']}")
                
                if 'reputation' in data:
                    profile_parts.append(f"מספר נקודות מוניטין: {data['reputation']}")
                
                # עוקבים ועוקב אחרי
                if 'followingCount' in data:
                    profile_parts.append(f"עוקב אחרי: {data['followingCount']} משתמשים")
                
                if 'followerCount' in data:
                    profile_parts.append(f"מספר עוקבים: {data['followerCount']}")
                
                # חיבור כל החלקים לטקסט אחד
                profile_text = ". ".join(profile_parts)
                print(f"טקסט פרופיל מוכן: {profile_text}")
                
                return profile_text
                
            else:
                print(f"שגיאה בקבלת נתוני פרופיל: {response.status_code}")
                print(f"URL שנוסה: {response.url}")
                print(f"תוכן התגובה: {response.text[:200]}")
                return None
            
        except Exception as e:
            print(f"שגיאה בקבלת נתוני פרופיל: {str(e)}")
            return None
    
    def get_user_posts(self, username):
        try:
            response = self.session.get(
                f"{self.base_url}/api/user/{username}/posts",
                headers=self.headers,
                verify=False
            )
            return response.json()
        except Exception as e:
            print(f"שגיאה בקבלת פוסטים: {str(e)}")
            return None

class RecentPostsAPI:
    def __init__(self):
        self.base_url = "https://mitmachim.top"
        self.session = requests.Session()
        self.session.verify = False
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        }

    def get_recent_topics(self, limit=10):
        """
        מושך את הנושאים האחרונים מהפורום
        """
        try:
            # שינוי ה-endpoint ל-/api/recent/posts
            response = self.session.get(
                f"{self.base_url}/api/recent/posts",  # זה השינוי - במקום /api/recent
                params={'count': limit},
                headers=self.headers
            )
            
            if not response.ok:
                print(f"שגיאה בקבלת נושאים אחרונים: {response.status_code}")
                print(f"תוכן התגובה: {response.text[:200]}")
                return None

            posts_data = response.json()
            if not posts_data:
                print("לא התקבלו נתונים מהשרת")
                return None

            # מיפוי הפוסטים לנושאים
            topics = []
            seen_tids = set()  # למניעת כפילויות
            
            for post in posts_data:
                topic = post.get('topic', {})
                tid = topic.get('tid')
                
                if tid and tid not in seen_tids:
                    seen_tids.add(tid)
                    topics.append({
                        'tid': tid,
                        'title': topic.get('title', 'נושא ללא כותרת'),
                        'timestamp': post.get('timestamp', 0)
                    })
                    
                    if len(topics) >= limit:
                        break

            if topics:
                print(f"נמצאו {len(topics)} נושאים אחרונים")
                return topics
            else:
                print("לא נמצאו נושאים אחרונים לאחר העיבוד")
                return None

        except Exception as e:
            print(f"שגיאה בקבלת נושאים אחרונים: {str(e)}")
            return None

    def get_topic_posts(self, topic_id):
        """
        מושך את כל הפוסטים של נושא ספציפי
        """
        try:
            response = self.session.get(
                f"{self.base_url}/api/topic/{topic_id}",
                headers=self.headers
            )
            
            if not response.ok:
                return None

            topic_data = response.json()
            return {
                'title': topic_data.get('title', ''),
                'posts': sorted(topic_data.get('posts', []), key=lambda x: x.get('timestamp', 0))
            }

        except Exception as e:
            print(f"שגיאה בקבלת פוסטים של נושא: {str(e)}")
            return None

    def upload_to_yemot(self, yemot_api, limit=10):
        """
        מעלה את הנושאים האחרונים לשלוחה 2
        """
        if not yemot_api.token:
            print("נדרשת התחברות לימות תחילה")
            return False

        # שליפת הנושאים האחרונים
        print("\nמושך נושאים אחרונים...")
        topics = self.get_recent_topics(limit)
        if not topics:
            print("לא נמצאו נושאים אחרונים")
            return False

        # הכנת טקסט האינדקס הראשי
        index_text = "רשימת הנושאים האחרונים:\n"
        
        # מעבר על כל נושא והעלאת התוכן שלו
        for topic_index, topic in enumerate(topics, 1):
            topic_id = topic.get('tid')
            title = topic.get('title', 'נושא ללא כותרת')
            
            print(f"\nמטפל בנושא {topic_index}: {title}")
            index_text += f"להאזנה לנושא {title}, הקש {topic_index}.\n"
            
            # קבלת כל הפוסטים של הנושא
            topic_data = self.get_topic_posts(topic_id)
            if not topic_data:
                continue
                
            # העלאת הקדמה לנושא
            intro_text = f"נושא מספר {topic_index}: {topic_data['title']}. מכיל {len(topic_data['posts'])} תגובות."
            data = {
                "token": yemot_api.token,
                "what": f"ivr2:/2/{topic_index}/000.tts",
                "contents": clean_text_for_tts(intro_text)
            }
            
            try:
                print(f"מעלה הקדמה לנושא {topic_index}")
                response = requests.post(f"{yemot_api.base_url}UploadTextFile", data=data)
                if response.status_code == 200 and response.json().get('responseStatus') == 'OK':
                    print("הקדמה הועלתה בהצלחה")
            except Exception as e:
                print(f"שגיאה בהעלאת הקדמה: {str(e)}")
            
            # העלאת כל הפוסטים בנושא
            for post_index, post in enumerate(topic_data['posts'], 1):
                username = post.get('user', {}).get('username', 'משתמש לא ידוע')
                content = post.get('content', '')
                
                # ניקוי התוכן
                soup = BeautifulSoup(content, 'html.parser')
                clean_content = soup.get_text(strip=True)
                
                post_text = f"תגובה מספר {post_index} מאת {username}. {clean_content}"
                
                data = {
                    "token": yemot_api.token,
                    "what": f"ivr2:/2/{topic_index}/{post_index:03d}.tts",
                    "contents": clean_text_for_tts(post_text)
                }
                
                try:
                    print(f"מעלה תגובה {post_index} בנושא {topic_index}")
                    response = requests.post(f"{yemot_api.base_url}UploadTextFile", data=data)
                    if response.status_code == 200 and response.json().get('responseStatus') == 'OK':
                        print(f"תגובה {post_index} הועלתה בהצלחה")
                except Exception as e:
                    print(f"שגיאה בהעלאת תגובה: {str(e)}")
                
                time.sleep(1)
            
            time.sleep(2)

        # העלאת קובץ האינדקס הראשי
        print("\nמעלה את קובץ האינדקס הראשי...")
        data = {
            "token": yemot_api.token,
            "what": "ivr2:/2/M1000.tts",
            "contents": clean_text_for_tts(index_text)
        }
        
        try:
            response = requests.post(f"{yemot_api.base_url}UploadTextFile", data=data)
            if response.status_code == 200 and response.json().get('responseStatus') == 'OK':
                print("קובץ האינדקס הראשי הועלה בהצלחה")
        except Exception as e:
            print(f"שגיאה בהעלאת קובץ האינדקס: {str(e)}")

        return True

class CategoryTopicsAPI:
    def __init__(self):
        self.base_url = "https://mitmachim.top"
        self.session = requests.Session()
        self.session.verify = False
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        }

    def get_category_topics(self, category_id, limit=10):
        """
        מושך את הנושאים האחרונים מקטגוריה ספציפית
        :param category_id: מזהה הקטגוריה
        :param limit: כמות הנושאים לשליפה
        :return: רשימה של נושאים אחרונים
        """
        try:
            print(f"מושך {limit} נושאים אחרונים מקטגוריה {category_id}...")
            
            response = self.session.get(
                f"{self.base_url}/api/category/{category_id}",
                params={
                    'topicCount': limit,
                    'sort': 'newest'  # מיון לפי החדשים ביותר
                },
                headers=self.headers
            )
            
            if not response.ok:
                print(f"שגיאה בקבלת נושאים: {response.status_code}")
                return None

            topics_data = response.json()
            return topics_data.get('topics', [])

        except Exception as e:
            print(f"שגיאה בקבלת נושאים: {str(e)}")
            return None

    def get_topic_posts(self, topic_id):
        """
        מושך את כל הפוסטים של נושא ספציפי
        :param topic_id: מזהה הנושא
        :return: רשימה של פוסטים מסודרת לפי תאריך
        """
        try:
            print(f"מושך פוסטים מנושא {topic_id}...")
            
            response = self.session.get(
                f"{self.base_url}/api/topic/{topic_id}",
                headers=self.headers
            )
            
            if not response.ok:
                print(f"שגיאה בקבלת פוסטים: {response.status_code}")
                return None

            topic_data = response.json()
            posts = topic_data.get('posts', [])
            
            # מיון הפוסטים לפי תאריך
            posts.sort(key=lambda x: x.get('timestamp', 0))
            
            return posts

        except Exception as e:
            print(f"שגיאה בקבלת פוסטים: {str(e)}")
            return None

    def prepare_topic_tts(self, topic, posts, topic_index):
        """
        מכין את תוכן ה-TTS עבור נושא ופוסטים
        :param topic: מידע על הנושא
        :param posts: רשימת הפוסטים
        :param topic_index: אינדקס הנושא (1-10)
        :return: רשימה של קבצי TTS לנושא
        """
        tts_files = []
        
        # הכנת הקדמה לנושא
        topic_intro = f"{topic.get('title', '')}. "
        topic_intro += f"נפתח על ידי {topic.get('user', {}).get('username', 'משתמש לא ידוע')}. "
        topic_intro += f"מספר תגובות: {len(posts)}."
        
        # כל נושא מקבל את המספר שלו כתת-שלוחה
        extension_number = topic_index  # שלוחה 1 לנושא 1, שלוחה 2 לנושא 2 וכו'
        
        tts_files.append({
            'text': clean_text_for_tts(topic_intro),
            'filename': f"4/{extension_number}/000.tts"  # הקדמה לנושא
        })
        
        # הכנת כל הפוסטים
        for post_index, post in enumerate(posts, 1):
            username = post.get('user', {}).get('username', 'משתמש לא ידוע')
            content = post.get('content', '')
            
            # ניקוי התוכן
            soup = BeautifulSoup(content, 'html.parser')
            clean_content = soup.get_text(strip=True)
            
            post_text = f"תגובה מספר {post_index} מאת {username}. {clean_content}"
            
            tts_files.append({
                'text': clean_text_for_tts(post_text),
                'filename': f"4/{extension_number}/{post_index:03d}.tts"
            })
        
        return tts_files

    def upload_to_yemot(self, yemot_api, category_id=66, topic_limit=10):
        """
        מעלה את כל הנושאים והפוסטים לימות
        :param yemot_api: מופע של YemotAPI
        :param category_id: מזהה הקטגוריה
        :param topic_limit: מספר הנושאים לשליפה
        """
        if not yemot_api.token:
            print("נדרשת התחברות לימות תחילה")
            return False

        # שליפת הנושאים האחרונים
        topics = self.get_category_topics(category_id, topic_limit)
        if not topics:
            print("לא נמצאו נושאים")
            return False

        print(f"\nנמצאו {len(topics)} נושאים, מתחיל בהעלאה...")

        # עיבוד והעלאת כל נושא
        success_count = 0
        total_files = 0
        
        for topic_index, topic in enumerate(topics, 1):
            posts = self.get_topic_posts(topic.get('tid'))
            if posts:
                # הכנת קבצי ה-TTS לנושא הנוכחי
                topic_files = self.prepare_topic_tts(topic, posts, topic_index)
                total_files += len(topic_files)
                
                # העלאת כל הקבצים של הנושא הנוכחי
                for file_info in topic_files:
                    try:
                        data = {
                            "token": yemot_api.token,
                            "what": f"ivr2:/{file_info['filename']}",
                            "contents": file_info['text']
                        }
                        
                        print(f"\nמעלה קובץ: {file_info['filename']}")
                        print(f"תוכן: {file_info['text'][:100]}...")
                        
                        response = requests.post(f"{yemot_api.base_url}UploadTextFile", data=data)
                        
                        if response.status_code == 200 and response.json().get('responseStatus') == 'OK':
                            print("הקובץ הועלה בהצלחה")
                            success_count += 1
                        else:
                            print(f"שגיאה בהעלאת הקובץ")
                        
                        time.sleep(2)  # המתנה בין העלאות
                        
                    except Exception as e:
                        print(f"שגיאה בהעלאת קובץ: {str(e)}")
            
            time.sleep(1)  # המתנה בין נושאים

        print(f"\nהועלו {success_count} קבצים מתוך {total_files}")
        return success_count > 0
        

def get_nodebb_content(url, username, password):
    try:
        nodebb = NodeBBAPI()
        
        print(f"מנסה להתחבר עם המשתמש: {username}")
        if not nodebb.login(username, password):
            return None

        # אם זה דף התראות
        if 'notifications' in url:
            print("מבקש התראות מהשרת...")
            notifications = nodebb.get_notifications()
            if notifications and isinstance(notifications, list):
                print(f"התקבלו {len(notifications)} התראות, מעבד כל אחת בנפרד...")
                result = []
                # נוסיף מספור לכל התראה
                for i, notification in enumerate(notifications, 1):
                    # יצירת מילון עם המידע הנדרש
                    result.append({
                        'text': notification,
                        'filename': f'notification_{i:03d}'  # לדוגמה: notification_001, notification_002 וכו'
                    })
                return result
            else:
                print("לא התקבלו התראות תקינות מהשרת")
        
        return None
            
    except Exception as e:
        print(f"שגיאה בקריאת תוכן מ-NodeBB: {str(e)}")
        return None



def main():
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"Current Date and Time (UTC - YYYY-MM-DD HH:MM:SS formatted): {current_time}")
    print("Current User's Login: MMDARTYQO")
    print("התוכנית מתחילה...")
    
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
            
            # יצירת מילון משתמשים מהנתונים
            users = {}
            for record in users_data:
                if record.get('מצב הזמנה') == 'מאושר':
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
                    
                    # העלאת התראות לשלוחה 1/X
                    notifications = nodebb.get_notifications()
                    if notifications:
                        for index, notification in enumerate(notifications):
                            if len(notification) > 10:
                                data = {
                                    "token": api.token,
                                    "what": f"ivr2:/1/{user_data['sub_extension']}/{index:03d}.tts",
                                    "contents": clean_text_for_tts(notification, index + 1)
                                }
                                try:
                                    response = requests.post(f"{api.base_url}UploadTextFile", data=data)
                                    if response.status_code == 200 and response.json().get('responseStatus') == 'OK':
                                        print(f"התראה {index + 1} הועלתה בהצלחה למשתמש {username}")
                                except Exception as e:
                                    print(f"שגיאה בהעלאת התראה: {str(e)}")
                                time.sleep(2)
                    
                    # העלאת פרופיל לשלוחה 3/X
                    profile_text = nodebb.get_user_profile(user_data['forum_username'])
                    if profile_text:
                        data = {
                            "token": api.token,
                            "what": f"ivr2:/3/{user_data['sub_extension']}/000.tts",
                            "contents": clean_text_for_tts(profile_text)
                        }
                        try:
                            response = requests.post(f"{api.base_url}UploadTextFile", data=data)
                            if response.status_code == 200 and response.json().get('responseStatus') == 'OK':
                                print(f"פרופיל הועלה בהצלחה למשתמש {username}")
                        except Exception as e:
                            print(f"שגיאה בהעלאת פרופיל: {str(e)}")
                else:
                    print(f"ההתחברות לפורום נכשלה עבור {username}")

            # === שלוחה 2 - פוסטים אחרונים ===
            print("\nמתחיל בטיפול בפוסטים אחרונים לשלוחה 2...")
            recent_posts_api = RecentPostsAPI()
            recent_posts_api.upload_to_yemot(api, limit=10)

            # === שלוחה 4 - נושאים מקטגוריית "כללי - עזרה הדדית" ===
            print("\nמתחיל בטיפול בנושאי הפורום לשלוחה 4...")
            forum_api = CategoryTopicsAPI()
            forum_api.upload_to_yemot(api, category_id=66, topic_limit=10)

        else:
            print("שגיאה בקריאת קובץ YMGR")
            return
            
    except Exception as e:
        print(f"שגיאה בקריאת קובץ YMGR: {str(e)}")
        return

    print("התוכנית הסתיימה")

if __name__ == "__main__":
    main()
