import requests
import pickle
import random
import re
import os
import json, yaml
import onetimepass as otp
from time import sleep
from typing import BinaryIO , Dict , List , Union
import base64
import logging.config ,sys

__verison__ = "0.23.03.01.0"

def outputLog(projectName):
    log = logging.getLogger(f"{projectName}")
    log.setLevel(level=logging.DEBUG)
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s]\t%(message)s')
    # 输出日志到终端
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.level = logging.INFO
    console_handler.formatter = formatter
    log.addHandler(console_handler)
    #输出日志到文件
    file_handler = logging.FileHandler(f'{projectName}.log', encoding='utf-8')
    file_handler.formatter = formatter
    file_handler.level = logging.DEBUG
    log.addHandler(file_handler)
    return log

log = outputLog("CaoLiu_AutoReply")

try:
    with open("config.yml", "r+", encoding='utf8') as file:
        config = yaml.load(file, Loader=yaml.FullLoader)
except FileNotFoundError:
    log.error("配置文件“config.yml”不存在！")
    os._exit(0)

userid : str = config.get("gobal_config").get("truecaptcha_config").get("userid")
apikey : str = config.get("gobal_config").get("truecaptcha_config").get("apikey")
usersList = config.get("users_config")
PollingTime : int = config.get("gobal_config").get("PollingTime", 5)
ReplyLimit : int = config.get("gobal_config").get("ReplyLimit", 10)
Forbid : bool = config.get("gobal_config").get("Forbid", True)
Input_self : bool = config.get("gobal_config").get("Input_self", False)
Like : bool = config.get("gobal_config").get("Like", True)
TimeIntervalStart : bool = config.get("gobal_config").get("TimeIntervalStart", 1024)
TimeIntervalEnd : bool = config.get("gobal_config").get("TimeIntervalEnd", 2048)
ReplyContent : List = config.get("gobal_config").get("ReplyContent")
ForbidContent : List = config.get("gobal_config").get("ForbidContent")

def save_cookies(session : requests.Session , filename : str) -> None:
    with open(filename, 'wb') as f:
        try:
            pickle.dump(session.cookies, f)
            log.debug(f"save {filename} success")
        except:
            ...

def load_cookies(session : requests.Session , filename : str) -> None:
    with open(filename, 'rb') as f:
        try:
            session.cookies.update(pickle.load(f))
            log.debug(f"load {filename} success")
        except:
            ...

def apitruecaptcha(content : BinaryIO) -> str:
    image=base64.b64encode(content)
    url='https://api.apitruecaptcha.org/one/gettext'
    data={
        'data':str(image,'utf-8'),
        'userid':userid,
        'apikey':apikey
    }
    result = requests.post(url, json.dumps(data))
    res=result.json()
    try:
        code = res['result']
    except:
        log.debug(f"api error,{str(res)}")
        code = "XXXX"
    log.debug("apitruecaptcha code: %s" % code)
    return code

def ttshitu(content : BinaryIO) -> str:
    image=base64.b64encode(content)
    host='http://api.ttshitu.com/base64'
    headers={
        'Content-Type':'application/json;charset=UTF-8'
    }
    data={
        'username': userid ,
        'password': apikey ,
        'image':image.decode('utf-8')
    }
    res=requests.post(url=host,data=json.dumps(data))
    res=res.text
    res=json.loads(res)
    res=res['data']['result']
    return res

class User:
    Like : bool = False
    Retry : int = 5
    RetryList : int = 10
    Host : str = f"https://{config.get('gobal_config').get('Host', 't66y.com')}/"
    Index : str = f"{Host}index.php"
    Login : str = f"{Host}login.php"
    Post : str = f"{Host}post.php?"
    Today : str = f"{Host}thread0806.php?fid=7&search=today"
    VerCode : str = f"{Host}require/codeimg.php?"
    Api : str = f"{Host}api.php"
    UserAgent : str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36"
    ReplyList : List = []
    Invalid : bool = False
    SleepTime : int = 0
    ReplyCount : int = ReplyLimit
    Headers : Dict = {
        'Host': Host.split("//")[1].replace("/", ""),
        'Proxy-Connection': 'keep-alive',
        'Referer': Login,
        'User-Agent': UserAgent
    }

    def __init__(self, username : str , password : str , secret : str) -> None:
        self.username : str = username
        self.password : str = password
        self.secret : str = secret
        self.cookies : requests.cookies = None
        self.s : requests.Session = requests.Session()
        file : str = f"./{username}.cookies"
        if os.path.exists(file):
            load_cookies(self.s, file)
            if self.is_valid_cookies():
                if self.is_ban_cookies():
                    self.set_invalid()
                    return
                else:
                    self.cookies = self.s.cookies
                    log.info(f"{self.username} cookies is valid , login success")
                    return
            else:
                log.info(f"{self.username} cookies is invalid , login again")
        if self.login():
            self.cookies = self.s.cookies
            save_cookies(self.s, file)
            if self.is_ban_cookies():
                self.set_invalid()
                return
            log.info(f"{self.username} login success") 
        else:
            log.info(f"{self.username} login failed")
            self.set_invalid()

    def login(self) -> None:
        def login1():
            sleep(2)
            data : Dict = {
            'pwuser': self.username,
            'pwpwd':  self.password,
            'hideid': '0',
            'cktime': '0',
            'forward': self.Post,
            'jumpurl': self.Post,
            'step': '2'
            }
            login = self.s.post(self.Login , headers = self.Headers , data = data)
            return login.text

        def login2():
            sleep(2)
            token = otp.get_totp(self.secret)
            data = {
            'step': '2',
            'cktime': '0',
            'oneCode': token
            }
            login=self.s.post(self.Login , headers = self.Headers , data = data)
            return login.text

        def captcha():
            sleep(2)
            code = random.uniform(0,1)
            code = round(code,16)
            VerCode = self.VerCode + str(code)
            image = self.s.get(VerCode , headers = self.Headers)
            if Input_self:
                with open("./captcha.png", "wb") as f:
                    f.write(image.content)
                vercode = input("请输入验证码: ")
            else:
                vercode = apitruecaptcha(image.content)
            data={
                'validate': vercode
            }
            login = self.s.post(self.Login , data = data , headers = self.Headers)
            if "驗證碼不正確，請重新填寫" in login.text:
                log.info(f"{self.username} captcha with code: {vercode} failed")
            else:
                log.info(f"{self.username} captcha with code: {vercode} success") 

        res = login1()
        if res.find("您已經順利登錄") != -1:
            return True
        elif res.find("賬號已開啟兩步驗證") != -1:
            res = login2()
            if res.find("您已經順利登錄") != -1:
                return True
        elif res.find("登录尝试次数过多") != -1:
            captcha()
            log.debug(f"{self.username} complete captcha")
            # 請輸入您的帳號與密碼
        
        if self.Retry > 0:
            log.debug(f"{self.username} retry login,remaining retry times: %d" % self.Retry)
            self.Retry -= 1
            if self.login():
                return True
        else:
            log.debug(f"{self.username} login failed!")
            return False

    #校验cookies是否有效
    def is_valid_cookies(self) -> bool:
        sleep(2)
        res = self.s.get(self.Index , headers = self.Headers)
        if res.text.find("上次登錄時間") != -1 :
            return True
        else:
            return False

    def is_ban_cookies(self) -> bool:
        sleep(2)
        res = self.s.get(self.Index , headers = self.Headers)
        if res.text.find("禁止發言") != -1 :
            return True
        else:
            return False

    def reply(self, url) -> bool:
        sleep(2)
        if self.ReplyCount == 0:
            log.info(f"{self.username} reply completed.The account has {self.get_user_USD()} USD now")
            return
        title = self.get_title(url)
        content = self.get_reply_content()
        tid = self.get_tid(url)
        data = {
            'atc_usesign':'1',
            'atc_convert':'1',
            'atc_autourl': '1',
            'atc_title':  title,
            'atc_content': content ,
            'step': '2',
            'action': 'reply',
            'fid': '7',
            'tid':  tid,
            'atc_attachment': 'none',
            'pid':'',
            'article':'',
            'touid':'',
            'verify':'verify'
        }
        res = requests.post(url = self.Post , data = data , headers = self.Headers , cookies = self.cookies )
        if res.text.find("發貼完畢點擊進入主題列表") != -1:
            self.ReplyCount -= 1
            log.info(f"{self.username} reply {title} with {content} success , remaining reply times: {self.ReplyCount}" )
            return True
        elif res.text.find("灌水預防機制") != -1:
            log.info(f"{self.username} reply failed , user replay too frequency")
            return True
        elif res.text.find("所屬的用戶組") != -1:
            log.info(f"{self.username} reply failed , day reply times is over")
            return False
        elif res.text.find("管理員禁言, 類型為永久禁言") != -1:
            log.info(f"{self.username} reply failed , user is banned")
            return False
        elif res.text.find("帖子ID非法") != -1:
            log.info(f"{self.username} reply failed , {url} is invaild")
            return True
        else:
            log.error(f"{self.username} reply {url} failed , unknown error")
            log.error(res.text)
            return False

    def like(self, url : str) -> bool:
        if not Like or self.Like:
            return
        id = self.get_reply_id(url)
        if not id:
            return
        sleep(2)
        data={
            'action': 'clickLike',
            'id': id,
            'page': 'h',
            'json': '1',
            'url': url
        } 
        res = requests.post(self.Api , headers = self.Headers , data = data , cookies = self.cookies)
        try:
            if int(json.loads(res.text)['myMoney']) > 0 :
                log.info(f"{self.username} like success")
        except:
            return

    #简单浏览
    def browse(self, url : str) -> None:
        sleep(2)
        res = requests.get(url = url , headers = self.Headers , cookies = self.cookies)
    
    #获取今日帖子
    def get_today_list(self):
        sleep(2)
        res = requests.get(self.Today , headers = self.Headers)
        content = res.text

        pat_title : str = ('htm_data/\w+/\w+/\w+.html')
        pat_moderator : str = "版主:([\s\S]*?)<\/span>"
        pat_username : str = "username=(\w+)"
        pat_user : str = 'class="bl">(.*)?</a>'
        pat_all_title : str = '<h3><a href="([\s\S]*?)"'
        pat_all_content : str = '<h3><a href=".*" target="_blank" id=".*">(.*)<\/a><\/h3>'
        moderator : str = re.search(pat_moderator, content).group(0)
        username : List = re.findall(pat_username, moderator)
        content = res.text[res.text.find('普通主題'):]
        all_username : List = re.findall(pat_user, content)
        title = re.findall(pat_title , content)
        all_title = re.findall(pat_all_title , content)
        all_content = re.findall(pat_all_content , content)

        log.debug(f"{self.username} get list number: {str(len(title))}")

        if len(all_title) != len(all_username):
            if self.RetryList > 0:
                log.debug(f"{self.username} get list number error , retry get list , remaining retry times: %d" % self.RetryList)
                self.RetryList -= 1
                sleep(2)
                self.get_today_list()
                return
            else:
                os._exit(0)

        
        if Forbid:
            black_list : List = []
            log.debug("moderator list: " + str(" ".join(username)))
            for index in range(len(all_username)):
                if all_username[index].strip() in moderator:
                    black_list.append(all_title[index])
            for item in black_list:
                try:
                    title.remove(item)
                except:
                    ...
                log.debug(f"{self.username} remove {item} from list")

            black_list : List = []
            for index in range(len(all_content)):
                content = all_content[index]
                for item in ForbidContent:
                    if item in content:
                        black_list.append(all_title[index])
                        break

            for item in black_list:
                try:
                    title.remove(item)
                except:
                    ...
                log.debug(f"{self.username} remove {item} from list")

        self.ReplyList = title
        log.debug(f"{self.username} get reply list number {str(len(title))}")

    #从今日列表中抽取出一个帖子
    def get_one_link(self) -> Union[str , None]:
        if len(self.ReplyList) == 0:
            return None
        url = self.ReplyList[random.randint(0,len(self.ReplyList)-1)]
        log.debug(f"{self.username} get one link: {url}")
        self.ReplyList.remove(url)
        return f"{self.Host}{url}"

    #从url中提取出tid
    def get_tid(self , url : str) -> str:
        pat_tid = "/(\d+).html"
        tid = re.search(pat_tid , url).group(1)
        return tid

    #获取回复内容的id用于点赞
    def get_reply_id(self, url : str) -> Union[str , None]:
        sleep(2)
        res = requests.get(url = url , headers = self.Headers , cookies = self.cookies)
        reply_id_list = re.findall("<a name=#(\d+)><\/a>", res.text)
        if len(reply_id_list) == 0:
            return None
        else:
            return reply_id_list[random.randint(0,len(reply_id_list)-1)]

    #获取给定url的主题名字
    def get_title(self , url : str) -> str:
        sleep(2)
        res = requests.get(url = url , headers = self.Headers , cookies = self.cookies)
        pat_title = '<b>本頁主題:</b> .*</td>'
        try:
            title = re.search(pat_title, res.text).group(0)
            title = "Re:" + title.replace('<b>本頁主題:</b> ','').replace('</td>','')
        except:
            title = "Re: "
        return title

    #随机获取回复内容
    def get_reply_content(self) -> str:
        return ReplyContent[random.randint(0,len(ReplyContent)-1)]

    # 获取回复次数
    def get_reply_number(self) -> str:
        sleep(2)
        res = requests.get(self.Index , headers = self.Headers , cookies = self.cookies)
        pat_reply_number = "共發表帖子: \d{1,5}"
        reply_number = re.search(pat_reply_number , res.text).group(0).replace('共發表帖子: ','')
        return reply_number

    def get_user_USD(self) -> str:
        sleep(2)
        res = requests.get(self.Index , headers = self.Headers , cookies = self.cookies)
        pat_user_USD = "威望: \d{1,3}"
        user_USD = re.search(pat_user_USD , res.text).group(0).replace('威望: ','')
        return user_USD

    def get_username(self) -> str:
        return self.username

    def set_invalid(self) -> None:
        log.debug(f"{self.username} is invalid")
        self.Invalid = True

    def get_invalid(self) -> bool:
        return self.Invalid

    def set_sleep_time(self , time : int) -> None:
        self.SleepTime = time

    def get_sleep_time(self) -> int:
        return self.SleepTime

users = []
for i in range(len(usersList)):
    user=User(usersList[i]['user'],usersList[i]['password'],usersList[i]['secret'])
    if user.get_invalid():
        continue
    user.get_today_list()
    users.append(user)

init_sleep_time=0
allUser_ww=[]
start_sleep = 0
while True:
    return_flag = True
    sleep_time = random.randint(TimeIntervalStart,TimeIntervalEnd)
    if init_sleep_time == 0:
        random.shuffle(users)
    for user in users:        
        if user.get_invalid():
            continue
        else:
            return_flag = False
        if init_sleep_time == 0:
            user_name = user.get_username()
            allUser_ww.append(f"{user_name}: {user.get_user_USD()} 威望")
            log.info(f"{user_name} init {start_sleep} seconds")
            user.set_sleep_time(start_sleep)
            start_sleep += random.randint(540, 640)
            continue
        if user.get_sleep_time() > 0:
            user.set_sleep_time(user.get_sleep_time() - PollingTime)
            continue
        url = user.get_one_link()
        if url is None:
            user.set_invalid()
            continue
        user.browse(url)
        if not user.reply(url):
            user.set_invalid()
            continue        
        user.like(url)
        log.debug(f"{user.get_username()} sleep {sleep_time} seconds")
        user.set_sleep_time(sleep_time)

    if return_flag:
        os._exit(0)
    
    if init_sleep_time == 0:
        # 日志输出: 全部用户名威望值
        log.info("--------------------->>>")
        for u in allUser_ww:
            log.info(u)
        # 关闭初始化睡眠
        init_sleep_time = 1
        log.info("--------------------->>>")
    sleep(PollingTime)
