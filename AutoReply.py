import requests
import pickle
import random
import re
import os
import json
import onetimepass as otp
from time import sleep
from typing import BinaryIO , Dict , List , Union
import base64
import logging

__verison__ = "0.23.02.05.1"

#从 https://truecaptcha.org/ 处注册获取userid和apikey
userid : str = "xxxx"
apikey : str = "xxxx"

#用户名 密码 2FA原始密钥16位或32位 多个账号用空格分隔
user : str = "xxxx xxxx"
password : str = "xxxx xxxx"
secret : str = "xxxx xxxx"

#循环间隔
PollingTime : int = 5
#回复次数限制
ReplyLimit : int = 10
#禁止版主帖子回复和关键字屏蔽
Forbid : bool = True
#手动输入验证码
Input_self : bool = False
#每日点赞
Like : bool = True
#时间间隔最小
TimeIntervalStart : bool = 1024
#时间间隔最大
TimeIntervalEnd : bool = 2048
#回复内容
ReplyContent : List = ['感谢分享','感谢你的分享','谢谢分享','多谢分享','感谢作者的分享','谢谢坛友分享','内容精彩','的确如此','感谢分享','涨知识了','很有意思']
#关键字屏蔽，主要防止签到贴
ForbidContent : List = ['签到','专用贴','禁止无关回复']

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
FORMAT = '%(asctime)s %(message)s'
logging.basicConfig(format=FORMAT)

def save_cookies(session : requests.Session , filename : str) -> None:
    with open(filename, 'wb') as f:
        try:
            pickle.dump(session.cookies, f)
            logger.debug(f"save {filename} success")
        except:
            ...

def load_cookies(session : requests.Session , filename : str) -> None:
    with open(filename, 'rb') as f:
        try:
            session.cookies.update(pickle.load(f))
            logger.debug(f"load {filename} success")
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
        logger.debug(f"api error,{str(res)}")
        code = "XXXX"
    logger.debug("apitruecaptcha code: %s" % code)
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
    Host : str = "https://t66y.com/"
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
                    logger.info(f"{self.username} cookies is valid , login success")
                    return
            else:
                logger.info(f"{self.username} cookies is invalid , login again")
        if self.login():
            self.cookies = self.s.cookies
            save_cookies(self.s, file)
            if self.is_ban_cookies():
                self.set_invalid()
                return
            logger.info(f"{self.username} login success") 
        else:
            logger.info(f"{self.username} login failed")
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
                logger.info(f"{self.username} captcha with code: {vercode} failed")
            else:
                logger.info(f"{self.username} captcha with code: {vercode} success") 

        res = login1()
        if res.find("您已經順利登錄") != -1:
            return True
        elif res.find("賬號已開啟兩步驗證") != -1:
            res = login2()
            if res.find("您已經順利登錄") != -1:
                return True
        elif res.find("登录尝试次数过多") != -1:
            captcha()
            logger.debug(f"{self.username} complete captcha")
            # 請輸入您的帳號與密碼
        
        if self.Retry > 0:
            logger.debug(f"{self.username} retry login,remaining retry times: %d" % self.Retry)
            self.Retry -= 1
            if self.login():
                return True
        else:
            logger.debug(f"{self.username} login failed!")
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

    def reply(self, url) -> None:
        sleep(2)
        if self.ReplyCount == 0:
            logger.info(f"{self.username} reply completed")
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
            logger.info(f"{self.username} reply {title} with {content} success , remaining reply times: %d" % self.ReplyCount)
            return True
        elif res.text.find("灌水預防機制") != -1:
            logger.info(f"{self.username} reply failed , user replay too frequency")
            return True
        elif res.text.find("所屬的用戶組") != -1:
            logger.debug(f"{self.username} reply failed , day reply times is over")
            return False
        elif res.text.find("管理員禁言, 類型為永久禁言") != -1:
            logger.debug(f"{self.username} reply failed , user is banned")
            return False
        else:
            logger.debug(f"{self.username} reply failed , unknown error")
            logger.error(res.text)
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
                logger.info(f"{self.username} like success")
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

        logger.debug(f"{self.username} get list number: {str(len(title))}")

        if len(all_title) != len(all_username):
            if self.RetryList > 0:
                logger.debug(f"{self.username} get list number error , retry get list , remaining retry times: %d" % self.RetryList)
                self.RetryList -= 1
                sleep(2)
                self.get_today_list()
                return
            else:
                os._exit(0)

        
        if Forbid:
            black_list : List = []
            logger.info("moderator list: " + str(" ".join(username)))
            for index in range(len(all_username)):
                if all_username[index].strip() in moderator:
                    black_list.append(all_title[index])
            for item in black_list:
                try:
                    title.remove(item)
                except:
                    ...
                logger.debug(f"{self.username} remove {item} from list")

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
                logger.debug(f"{self.username} remove {item} from list")

        self.ReplyList = title
        logger.debug(f"{self.username} get reply list number {str(len(title))}")

    #从今日列表中抽取出一个帖子
    def get_one_link(self) -> Union[str , None]:
        if len(self.ReplyList) == 0:
            return None
        url = self.ReplyList[random.randint(0,len(self.ReplyList)-1)]
        logger.debug(f"{self.username} get one link: {url}")
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

    def get_username(self) -> str:
        return self.username

    def set_invalid(self) -> None:
        logger.info(f"{self.username} is invalid")
        self.Invalid = True

    def get_invalid(self) -> bool:
        return self.Invalid

    def set_sleep_time(self , time : int) -> None:
        self.SleepTime = time

    def get_sleep_time(self) -> int:
        return self.SleepTime

userlist=user.split()
passwordlist=password.split()
secretlist=secret.split()

users = []
for i in range(len(userlist)):
    user=User(userlist[i],passwordlist[i],secretlist[i])
    if user.get_invalid():
        continue
    user.get_today_list()
    users.append(user)

while True:
    return_flag = True
    for user in users:        
        if user.get_invalid():
            continue
        else:
            return_flag = False
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
        sleep_time = random.randint(TimeIntervalStart,TimeIntervalEnd)
        logger.info(f"{user.get_username()} sleep {sleep_time} seconds")
        user.set_sleep_time(sleep_time)

    if return_flag:
        os._exit(0)

    sleep(PollingTime)
