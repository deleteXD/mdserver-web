# coding:utf-8

# ---------------------------------------------------------------------------------
# MW-Linux面板
# ---------------------------------------------------------------------------------
# copyright (c) 2018-∞(https://github.com/midoks/mdserver-web) All rights reserved.
# ---------------------------------------------------------------------------------
# Author: midoks <midoks@163.com>
# ---------------------------------------------------------------------------------

# ---------------------------------------------------------------------------------
# 核心方法库
# ---------------------------------------------------------------------------------


import os
import sys
import time
import string
import json
import hashlib
import shlex
import datetime
import subprocess
import re
import db
from random import Random


def execShell(cmdstring, cwd=None, timeout=None, shell=True):

    if shell:
        cmdstring_list = cmdstring
    else:
        cmdstring_list = shlex.split(cmdstring)
    if timeout:
        end_time = datetime.datetime.now() + datetime.timedelta(seconds=timeout)

    sub = subprocess.Popen(cmdstring_list, cwd=cwd, stdin=subprocess.PIPE,
                           shell=shell, bufsize=4096, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    while sub.poll() is None:
        time.sleep(0.1)
        if timeout:
            if end_time <= datetime.datetime.now():
                raise Exception("Timeout：%s" % cmdstring)

    if sys.version_info[0] == 2:
        return sub.communicate()

    data = sub.communicate()
    # python3 fix 返回byte数据
    if isinstance(data[0], bytes):
        t1 = str(data[0], encoding='utf-8')

    if isinstance(data[1], bytes):
        t2 = str(data[1], encoding='utf-8')
    return (t1, t2)


def getTracebackInfo():
    import traceback
    errorMsg = traceback.format_exc()
    return errorMsg


def getRunDir():
    return os.getcwd()


def getRootDir():
    return os.path.dirname(os.path.dirname(getRunDir()))


def getPluginDir():
    return getRunDir() + '/plugins'


def getPanelDataDir():
    return getRunDir() + '/data'


def getServerDir():
    return getRootDir() + '/server'


def getLogsDir():
    return getRootDir() + '/wwwlogs'


def getWwwDir():
    file = getRunDir() + '/data/site.pl'
    if os.path.exists(file):
        return readFile(file).strip()
    return getRootDir() + '/wwwroot'


def setWwwDir(wdir):
    file = getRunDir() + '/data/site.pl'
    return writeFile(file, wdir)


def getBackupDir():
    file = getRunDir() + '/data/backup.pl'
    if os.path.exists(file):
        return readFile(file).strip()
    return getRootDir() + '/backup'


def setBackupDir(bdir):
    file = getRunDir() + '/data/backup.pl'
    return writeFile(file, bdir)


def getAcmeDir():
    acme = '/root/.acme.sh'
    if isAppleSystem():
        cmd = "who | sed -n '2, 1p' |awk '{print $1}'"
        user = execShell(cmd)[0].strip()
        acme = '/Users/' + user + '/.acme.sh'
    if not os.path.exists(acme):
        acme = '/.acme.sh'
    return acme


def triggerTask():
    isTask = getRunDir() + '/tmp/panelTask.pl'
    writeFile(isTask, 'True')


def systemdCfgDir():
    # ubuntu
    cfg_dir = '/lib/systemd/system'
    if os.path.exists(cfg_dir):
        return cfg_dir

    # debian,centos
    cfg_dir = '/usr/lib/systemd/system'
    if os.path.exists(cfg_dir):
        return cfg_dir

    # local test
    return "/tmp"


def getSslCrt():
    if os.path.exists('/etc/ssl/certs/ca-certificates.crt'):
        return '/etc/ssl/certs/ca-certificates.crt'
    if os.path.exists('/etc/pki/tls/certs/ca-bundle.crt'):
        return '/etc/pki/tls/certs/ca-bundle.crt'
    return ''


def getOs():
    return sys.platform


def getOsName():
    cmd = "cat /etc/*-release | grep PRETTY_NAME |awk -F = '{print $2}' | awk -F '\"' '{print $2}'| awk '{print $1}'"
    data = execShell(cmd)
    return data[0].strip().lower()


def getOsID():
    cmd = "cat /etc/*-release | grep VERSION_ID | awk -F = '{print $2}' | awk -F '\"' '{print $2}'"
    data = execShell(cmd)
    return data[0].strip()


def getFileSuffix(file):
    tmp = file.split('.')
    ext = tmp[len(tmp) - 1]
    return ext


def isAppleSystem():
    if getOs() == 'darwin':
        return True
    return False


def isDebugMode():
    if isAppleSystem():
        return True

    debugPath = getRunDir() + "/data/debug.pl"
    if os.path.exists(debugPath):
        return True

    return False


def isNumber(s):
    try:
        float(s)
        return True
    except ValueError:
        pass

    try:
        import unicodedata
        unicodedata.numeric(s)
        return True
    except (TypeError, ValueError):
        pass

    return False


def deleteFile(file):
    if os.path.exists(file):
        os.remove(file)


def isInstalledWeb():
    path = getServerDir() + '/openresty/nginx/sbin/nginx'
    if os.path.exists(path):
        return True
    return False


def restartWeb():
    return opWeb("reload")


def opWeb(method):
    if not isInstalledWeb():
        return False

    # systemd
    systemd = '/lib/systemd/system/openresty.service'
    if os.path.exists(systemd):
        execShell('systemctl ' + method + ' openresty')
        return True

    # initd
    initd = getServerDir() + '/openresty/init.d/openresty'

    if os.path.exists(initd):
        execShell(initd + ' ' + method)
        return True

    return False


def restartMw():
    import system_api
    system_api.system_api().restartMw()


def checkWebConfig():
    op_dir = getServerDir() + '/openresty/nginx'
    cmd = "ulimit -n 10240 && " + op_dir + \
        "/sbin/nginx -t -c " + op_dir + "/conf/nginx.conf"
    result = execShell(cmd)
    searchStr = 'test is successful'
    if result[1].find(searchStr) == -1:
        msg = getInfo('配置文件错误: {1}', (result[1],))
        writeLog("软件管理", msg)
        return result[1]
    return True


def M(table):
    sql = db.Sql()
    return sql.table(table)


def getPage(args, result='1,2,3,4,5,8'):
    data = getPageObject(args, result)
    return data[0]


def getPageObject(args, result='1,2,3,4,5,8'):
    # 取分页
    import page
    # 实例化分页类
    page = page.Page()
    info = {}

    info['count'] = 0
    if 'count' in args:
        info['count'] = int(args['count'])

    info['row'] = 10
    if 'row' in args:
        info['row'] = int(args['row'])

    info['p'] = 1
    if 'p' in args:
        info['p'] = int(args['p'])
    info['uri'] = {}
    info['return_js'] = ''
    if 'tojs' in args:
        info['return_js'] = args['tojs']

    return (page.GetPage(info, result), page)


def md5(content):
    # 生成MD5
    try:
        m = hashlib.md5()
        m.update(content.encode("utf-8"))
        return m.hexdigest()
    except Exception as ex:
        return False


def getFileMd5(filename):
    # 文件的MD5值
    if not os.path.isfile(filename):
        return False

    myhash = hashlib.md5()
    f = file(filename, 'rb')
    while True:
        b = f.read(8096)
        if not b:
            break
        myhash.update(b)
    f.close()
    return myhash.hexdigest()


def getRandomString(length):
    # 取随机字符串
    str = ''
    chars = 'AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwXxYyZz0123456789'
    chrlen = len(chars) - 1
    random = Random()
    for i in range(length):
        str += chars[random.randint(0, chrlen)]
    return str


def getUniqueId():
    """
    根据时间生成唯一ID
    :return:
    """
    current_time = datetime.datetime.now()
    str_time = current_time.strftime('%Y%m%d%H%M%S%f')[:-3]
    unique_id = "{0}".format(str_time)
    return unique_id


def getJson(data):
    import json
    return json.dumps(data)


def returnData(status, msg, data=None):
    return {'status': status, 'msg': msg, 'data': data}


def returnJson(status, msg, data=None):
    # if data == None:
    #     return {'status': status, 'msg': msg}
    # return {'status': status, 'msg': msg, 'data': data}
    if data == None:
        return getJson({'status': status, 'msg': msg})
    return getJson({'status': status, 'msg': msg, 'data': data})


def getLanguage():
    path = 'data/language.pl'
    if not os.path.exists(path):
        return 'Simplified_Chinese'
    return readFile(path).strip()


def getStaticJson(name="public"):
    file = 'static/language/' + getLanguage() + '/' + name + '.json'
    if not os.path.exists(file):
        file = 'route/static/language/' + getLanguage() + '/' + name + '.json'
    return file


def returnMsg(status, msg, args=()):
    # 取通用字曲返回
    pjson = getStaticJson('public')
    logMessage = json.loads(readFile(pjson))
    keys = logMessage.keys()

    if msg in keys:
        msg = logMessage[msg]
        for i in range(len(args)):
            rep = '{' + str(i + 1) + '}'
            msg = msg.replace(rep, args[i])
    return {'status': status, 'msg': msg, 'data': args}


def getInfo(msg, args=()):
    # 取提示消息
    for i in range(len(args)):
        rep = '{' + str(i + 1) + '}'
        msg = msg.replace(rep, args[i])
    return msg


def getMsg(key, args=()):
    # 取提示消息
    try:
        pjson = getStaticJson('public')
        logMessage = json.loads(pjson)
        keys = logMessage.keys()
        msg = None
        if key in keys:
            msg = logMessage[key]
            for i in range(len(args)):
                rep = '{' + str(i + 1) + '}'
                msg = msg.replace(rep, args[i])
        return msg
    except:
        return key


def getLan(key):
    # 取提示消息
    pjson = getStaticJson('public')
    logMessage = json.loads(pjson)
    keys = logMessage.keys()
    msg = None
    if key in keys:
        msg = logMessage[key]
    return msg


def readFile(filename):
    # 读文件内容
    try:
        fp = open(filename, 'r')
        fBody = fp.read()
        fp.close()
        return fBody
    except Exception as e:
        # print(e)
        return False


def getDate():
    # 取格式时间
    import time
    return time.strftime('%Y-%m-%d %X', time.localtime())


def writeLog(stype, msg, args=()):
    # 写日志
    try:
        import time
        import db
        import json
        from flask import session
        uid = 1
        if 'uid' in session:
            uid = session['uid']
        sql = db.Sql()
        mdate = time.strftime('%Y-%m-%d %X', time.localtime())
        wmsg = getInfo(msg, args)
        data = (stype, wmsg, uid, mdate)
        result = sql.table('logs').add('type,log,uid,addtime', data)
        return True
    except Exception as e:
        return False


def writeFile(filename, content, mode='w+'):
    # 写文件内容
    try:
        fp = open(filename, mode)
        fp.write(content)
        fp.close()
        return True
    except Exception as e:
        return False


def backFile(file, act=None):
    """
        @name 备份配置文件
        @param file 需要备份的文件
        @param act 如果存在，则备份一份作为默认配置
    """
    file_type = "_bak"
    if act:
        file_type = "_def"

    # print("cp -p {0} {1}".format(file, file + file_type))
    execShell("cp -p {0} {1}".format(file, file + file_type))


def restoreFile(file, act=None):
    """
        @name 还原配置文件
        @param file 需要还原的文件
        @param act 如果存在，则还原默认配置
    """
    file_type = "_bak"
    if act:
        file_type = "_def"
    execShell("cp -p {1} {0}".format(file, file + file_type))


def enPunycode(domain):
    if sys.version_info[0] == 2:
        domain = domain.encode('utf8')
    tmp = domain.split('.')
    newdomain = ''
    for dkey in tmp:
        if dkey == '*':
            continue
        # 匹配非ascii字符
        match = re.search(u"[\x80-\xff]+", dkey)
        if not match:
            match = re.search(u"[\u4e00-\u9fa5]+", dkey)
        if not match:
            newdomain += dkey + '.'
        else:
            if sys.version_info[0] == 2:
                newdomain += 'xn--' + \
                    dkey.decode('utf-8').encode('punycode') + '.'
            else:
                newdomain += 'xn--' + \
                    dkey.encode('punycode').decode('utf-8') + '.'
    if tmp[0] == '*':
        newdomain = "*." + newdomain
    return newdomain[0:-1]


def dePunycode(domain):
    # punycode 转中文
    tmp = domain.split('.')
    newdomain = ''
    for dkey in tmp:
        if dkey.find('xn--') >= 0:
            newdomain += dkey.replace('xn--',
                                      '').encode('utf-8').decode('punycode') + '.'
        else:
            newdomain += dkey + '.'
    return newdomain[0:-1]


def enCrypt(key, strings):
    # 加密字符串
    try:
        if type(strings) != bytes:
            strings = strings.encode('utf-8')
        from cryptography.fernet import Fernet
        f = Fernet(key)
        result = f.encrypt(strings)
        return result.decode('utf-8')
    except:
        # print(get_error_info())
        return strings


def deCrypt(key, strings):
    # 解密字符串
    try:
        if type(strings) != bytes:
            strings = strings.decode('utf-8')
        from cryptography.fernet import Fernet
        f = Fernet(key)
        result = f.decrypt(strings).decode('utf-8')
        return result
    except:
        # print(get_error_info())
        return strings


def buildSoftLink(src, dst, force=False):
    '''
    建立软连接
    '''
    if not os.path.exists(src):
        return False

    if os.path.exists(dst) and force:
        os.remove(dst)

    if not os.path.exists(dst):
        execShell('ln -sf "' + src + '" "' + dst + '"')
        return True
    return False


def HttpGet(url, timeout=10):
    """
    发送GET请求
    @url 被请求的URL地址(必需)
    @timeout 超时时间默认60秒
    return string
    """
    if sys.version_info[0] == 2:
        try:
            import urllib2
            import ssl
            if sys.version_info[0] == 2:
                reload(urllib2)
                reload(ssl)
            try:
                ssl._create_default_https_context = ssl._create_unverified_context
            except:
                pass
            response = urllib2.urlopen(url, timeout=timeout)
            return response.read()
        except Exception as ex:
            return str(ex)
    else:
        try:
            import urllib.request
            import ssl
            try:
                ssl._create_default_https_context = ssl._create_unverified_context
            except:
                pass
            response = urllib.request.urlopen(url, timeout=timeout)
            result = response.read()
            if type(result) == bytes:
                result = result.decode('utf-8')
            return result
        except Exception as ex:
            return str(ex)


def HttpGet2(url, timeout):
    import urllib.request

    try:
        import ssl
        try:
            ssl._create_default_https_context = ssl._create_unverified_context
        except:
            pass
        req = urllib.request.urlopen(url, timeout=timeout)
        result = req.read().decode('utf-8')
        return result

    except Exception as e:
        return str(e)


def httpGet(url, timeout=10):
    return HttpGet2(url, timeout)


def HttpPost(url, data, timeout=10):
    """
    发送POST请求
    @url 被请求的URL地址(必需)
    @data POST参数，可以是字符串或字典(必需)
    @timeout 超时时间默认60秒
    return string
    """
    if sys.version_info[0] == 2:
        try:
            import urllib
            import urllib2
            import ssl
            ssl._create_default_https_context = ssl._create_unverified_context
            data = urllib.urlencode(data)
            req = urllib2.Request(url, data)
            response = urllib2.urlopen(req, timeout=timeout)
            return response.read()
        except Exception as ex:
            return str(ex)
    else:
        try:
            import urllib.request
            import ssl
            try:
                ssl._create_default_https_context = ssl._create_unverified_context
            except:
                pass
            data = urllib.parse.urlencode(data).encode('utf-8')
            req = urllib.request.Request(url, data)
            response = urllib.request.urlopen(req, timeout=timeout)
            result = response.read()
            if type(result) == bytes:
                result = result.decode('utf-8')
            return result
        except Exception as ex:
            return str(ex)


def httpPost(url, data, timeout=10):
    return HttpPost(url, data, timeout)


def writeSpeed(title, used, total, speed=0):
    # 写进度
    if not title:
        data = {'title': None, 'progress': 0,
                'total': 0, 'used': 0, 'speed': 0}
    else:
        progress = int((100.0 * used / total))
        data = {'title': title, 'progress': progress,
                'total': total, 'used': used, 'speed': speed}
    writeFile('/tmp/panelSpeed.pl', json.dumps(data))
    return True


def getSpeed():
    # 取进度
    path = getRootDir()
    data = readFile(path + '/tmp/panelSpeed.pl')
    if not data:
        data = json.dumps({'title': None, 'progress': 0,
                           'total': 0, 'used': 0, 'speed': 0})
        writeFile(path + '/tmp/panelSpeed.pl', data)
    return json.loads(data)


def getLastLineBk(inputfile, lineNum):
    # 读文件指定倒数行数
    try:
        fp = open(inputfile, 'rb')
        lastLine = ""
        lines = fp.readlines()
        count = len(lines)
        if count > lineNum:
            num = lineNum
        else:
            num = count
        i = 1
        lastre = []
        for i in range(1, (num + 1)):
            n = -i
            try:
                lastLine = lines[n].decode("utf-8", "ignore").strip()
            except Exception as e:
                lastLine = ""
            lastre.append(lastLine)

        fp.close()
        result = ''
        num -= 1
        while num >= 0:
            result += lastre[num] + "\n"
            num -= 1
        return result
    except Exception as e:
        return str(e)
        # return getMsg('TASK_SLEEP')


def getLastLine(path, num, p=1):
    pyVersion = sys.version_info[0]
    try:
        import html
        if not os.path.exists(path):
            return ""
        start_line = (p - 1) * num
        count = start_line + num
        fp = open(path, 'rb')
        buf = ""

        fp.seek(0, 2)
        if fp.read(1) == "\n":
            fp.seek(0, 2)
        data = []
        b = True
        n = 0

        for i in range(count):
            while True:
                newline_pos = str.rfind(str(buf), "\n")
                pos = fp.tell()
                if newline_pos != -1:
                    if n >= start_line:
                        line = buf[newline_pos + 1:]
                        try:
                            data.insert(0, html.escape(line))
                        except Exception as e:
                            pass
                    buf = buf[:newline_pos]
                    n += 1
                    break
                else:
                    if pos == 0:
                        b = False
                        break
                    to_read = min(4096, pos)
                    fp.seek(-to_read, 1)
                    t_buf = fp.read(to_read)
                    if pyVersion == 3:
                        if type(t_buf) == bytes:
                            t_buf = t_buf.decode("utf-8", "ignore").strip()
                    buf = t_buf + buf
                    fp.seek(-to_read, 1)
                    if pos - to_read == 0:
                        buf = "\n" + buf
            if not b:
                break
        fp.close()
    except Exception as e:
        return str(e)

    return "\n".join(data)


def downloadFile(url, filename):
    import urllib
    urllib.urlretrieve(url, filename=filename, reporthook=downloadHook)


def downloadHook(count, blockSize, totalSize):
    speed = {'total': totalSize, 'block': blockSize, 'count': count}
    print('%02d%%' % (100.0 * count * blockSize / totalSize))


def getLocalIpBack():
    # 取本地外网IP
    try:
        import re
        filename = 'data/iplist.txt'
        ipaddress = readFile(filename)
        if not ipaddress or ipaddress == '127.0.0.1':
            import urllib
            url = 'http://pv.sohu.com/cityjson?ie=utf-8'
            req = urllib.request.urlopen(url, timeout=10)
            content = req.read().decode('utf-8')
            ipaddress = re.search('\d+.\d+.\d+.\d+', content).group(0)
            writeFile(filename, ipaddress)

        ipaddress = re.search('\d+.\d+.\d+.\d+', ipaddress).group(0)
        return ipaddress
    except Exception as ex:
        # print(ex)
        return '127.0.0.1'


def getClientIp():
    from flask import request
    return request.remote_addr.replace('::ffff:', '')


def getLocalIp():
    filename = 'data/iplist.txt'
    try:
        ipaddress = readFile(filename)
        if not ipaddress or ipaddress == '127.0.0.1':
            cmd = "curl -4 -sS --connect-timeout 5 -m 60 https://v6r.ipip.net/?format=text"
            ip = execShell(cmd)
            result = ip[0].strip()
            if result == '':
                raise Exception("ipv4 is empty!")
            writeFile(filename, result)
            return result
        return ipaddress
    except Exception as e:
        cmd = "curl -6 -sS --connect-timeout 5 -m 60 https://v6r.ipip.net/?format=text"
        ip = execShell(cmd)
        result = ip[0].strip()
        if result == '':
            return '127.0.0.1'
        writeFile(filename, result)
        return result
    finally:
        pass
    return '127.0.0.1'


def inArray(arrays, searchStr):
    # 搜索数据中是否存在
    for key in arrays:
        if key == searchStr:
            return True

    return False


def formatDate(format="%Y-%m-%d %H:%M:%S", times=None):
    # 格式化指定时间戳
    if not times:
        times = int(time.time())
    time_local = time.localtime(times)
    return time.strftime(format, time_local)


def checkIp(ip):
    # 检查是否为IPv4地址
    import re
    p = re.compile(
        '^((25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(25[0-5]|2[0-4]\d|[01]?\d\d?)$')
    if p.match(ip):
        return True
    else:
        return False


def getHost(port=False):
    from flask import request
    host_tmp = request.headers.get('host')
    if not host_tmp:
        if request.url_root:
            tmp = re.findall(r"(https|http)://([\w:\.-]+)", request.url_root)
            if tmp:
                host_tmp = tmp[0][1]
    if not host_tmp:
        host_tmp = getLocalIp() + ':' + readFile('data/port.pl').strip()
    try:
        if host_tmp.find(':') == -1:
            host_tmp += ':80'
    except:
        host_tmp = "127.0.0.1:8888"
    h = host_tmp.split(':')
    if port:
        return h[-1]
    return ':'.join(h[0:-1])


def getClientIp():
    from flask import request
    return request.remote_addr.replace('::ffff:', '')


def checkDomainPanel():
    tmp = getHost()
    domain = readFile('data/bind_domain.pl')
    port = readFile('data/port.pl').strip()

    npid = getServerDir() + "/openresty/nginx/logs/nginx.pid"
    if not os.path.exists(npid):
        return False

    nconf = getServerDir() + "/web_conf/nginx/vhost/panel.conf"
    if os.path.exists(nconf):
        port = "80"

    if domain:
        client_ip = getClientIp()
        if client_ip in ['127.0.0.1', 'localhost', '::1']:
            return False
        if tmp.strip().lower() != domain.strip().lower():
            from flask import Flask, redirect, request, url_for
            to = "http://" + domain + ":" + str(port)
            return redirect(to, code=302)
    return False


def createLinuxUser(user, group):
    execShell("groupadd {}".format(group))
    execShell('useradd -s /sbin/nologin -g {} {}'.format(user, group))
    return True


def setOwn(filename, user, group=None):
    if isAppleSystem():
        return True

    # 设置用户组
    if not os.path.exists(filename):
        return False
    from pwd import getpwnam
    try:
        user_info = getpwnam(user)
        user = user_info.pw_uid
        if group:
            user_info = getpwnam(group)
        group = user_info.pw_gid
    except:
        if user == 'www':
            createLinuxUser(user)
        # 如果指定用户或组不存在，则使用www
        try:
            user_info = getpwnam('www')
        except:
            createLinuxUser(user)
            user_info = getpwnam('www')
        user = user_info.pw_uid
        group = user_info.pw_gid
    os.chown(filename, user, group)
    return True


def checkPort(port):
    # 检查端口是否合法
    ports = ['21', '443', '888']
    if port in ports:
        return False
    intport = int(port)
    if intport < 1 or intport > 65535:
        return False
    return True


def getStrBetween(startStr, endStr, srcStr):
    # 字符串取中间
    start = srcStr.find(startStr)
    if start == -1:
        return None
    end = srcStr.find(endStr)
    if end == -1:
        return None
    return srcStr[start + 1:end]


def getCpuType():
    cpuType = ''
    if isAppleSystem():
        cmd = "system_profiler SPHardwareDataType | grep 'Processor Name' | awk -F ':' '{print $2}'"
        cpuinfo = execShell(cmd)
        return cpuinfo[0].strip()

    # 取CPU类型
    cpuinfo = open('/proc/cpuinfo', 'r').read()
    rep = "model\s+name\s+:\s+(.+)"
    tmp = re.search(rep, cpuinfo, re.I)
    if tmp:
        cpuType = tmp.groups()[0]
    else:
        cpuinfo = execShell('LANG="en_US.UTF-8" && lscpu')[0]
        rep = "Model\s+name:\s+(.+)"
        tmp = re.search(rep, cpuinfo, re.I)
        if tmp:
            cpuType = tmp.groups()[0]
    return cpuType


def isRestart():
    # 检查是否允许重启
    num = M('tasks').where('status!=?', ('1',)).count()
    if num > 0:
        return False
    return True


def isUpdateLocalSoft():
    num = M('tasks').where('status!=?', ('1',)).count()
    if os.path.exists('mdserver-web.zip'):
        return True

    if num > 0:
        data = M('tasks').where('status!=?', ('1',)).field(
            'id,type,execstr').limit('1').select()
        argv = data[0]['execstr'].split('|dl|')
        if data[0]['type'] == 'download' and argv[1] == 'mdserver-web.zip':
            return True

    return False


def hasPwd(password):
    # 加密密码字符
    import crypt
    return crypt.crypt(password, password)


def getTimeout(url):
    start = time.time()
    result = httpGet(url)
    if result != 'True':
        return False
    return int((time.time() - start) * 1000)


def makeConf():
    file = getRunDir() + '/data/json/config.json'
    if not os.path.exists(file):
        c = {}
        c['title'] = '猫王面板'
        c['home'] = 'http://github/midoks/mdserver-web'
        c['recycle_bin'] = True
        c['template'] = 'default'
        writeFile(file, json.dumps(c))
        return c
    c = readFile(file)
    return json.loads(c)


def getConfig(k):
    c = makeConf()
    return c[k]


def setConfig(k, v):
    c = makeConf()
    c[k] = v
    file = getRunDir() + '/data/json/config.json'
    return writeFile(file, json.dumps(c))


def getHostAddr():
    if os.path.exists('data/iplist.txt'):
        return readFile('data/iplist.txt').strip()
    return '127.0.0.1'


def setHostAddr(addr):
    file = getRunDir() + '/data/iplist.txt'
    return writeFile(file, addr)


def getHostPort():
    if os.path.exists('data/port.pl'):
        return readFile('data/port.pl').strip()
    return '7200'


def setHostPort(port):
    file = getRunDir() + '/data/port.pl'
    return writeFile(file, port)


def auth_decode(data):
    # 解密数据
    token = GetToken()
    # 是否有生成Token
    if not token:
        return returnMsg(False, 'REQUEST_ERR')

    # 校验access_key是否正确
    if token['access_key'] != data['btauth_key']:
        return returnMsg(False, 'REQUEST_ERR')

    # 解码数据
    import binascii
    import hashlib
    import urllib
    import hmac
    import json
    tdata = binascii.unhexlify(data['data'])

    # 校验signature是否正确
    signature = binascii.hexlify(
        hmac.new(token['secret_key'], tdata, digestmod=hashlib.sha256).digest())
    if signature != data['signature']:
        return returnMsg(False, 'REQUEST_ERR')

    # 返回
    return json.loads(urllib.unquote(tdata))


# 数据加密
def auth_encode(data):
    token = GetToken()
    pdata = {}

    # 是否有生成Token
    if not token:
        return returnMsg(False, 'REQUEST_ERR')

    # 生成signature
    import binascii
    import hashlib
    import urllib
    import hmac
    import json
    tdata = urllib.quote(json.dumps(data))
    # 公式  hex(hmac_sha256(data))
    pdata['signature'] = binascii.hexlify(
        hmac.new(token['secret_key'], tdata, digestmod=hashlib.sha256).digest())

    # 加密数据
    pdata['btauth_key'] = token['access_key']
    pdata['data'] = binascii.hexlify(tdata)
    pdata['timestamp'] = time.time()

    # 返回
    return pdata


def checkToken(get):
    # 检查Token
    tempFile = 'data/tempToken.json'
    if not os.path.exists(tempFile):
        return False
    import json
    import time
    tempToken = json.loads(readFile(tempFile))
    if time.time() > tempToken['timeout']:
        return False
    if get.token != tempToken['token']:
        return False
    return True


def checkInput(data):
    # 过滤输入
    if not data:
        return data
    if type(data) != str:
        return data
    checkList = [
        {'d': '<', 'r': '＜'},
        {'d': '>', 'r': '＞'},
        {'d': '\'', 'r': '‘'},
        {'d': '"', 'r': '“'},
        {'d': '&', 'r': '＆'},
        {'d': '#', 'r': '＃'},
        {'d': '<', 'r': '＜'}
    ]
    for v in checkList:
        data = data.replace(v['d'], v['r'])
    return data


def checkCert(certPath='ssl/certificate.pem'):
    # 验证证书
    openssl = '/usr/local/openssl/bin/openssl'
    if not os.path.exists(openssl):
        openssl = 'openssl'
    certPem = readFile(certPath)
    s = "\n-----BEGIN CERTIFICATE-----"
    tmp = certPem.strip().split(s)
    for tmp1 in tmp:
        if tmp1.find('-----BEGIN CERTIFICATE-----') == -1:
            tmp1 = s + tmp1
        writeFile(certPath, tmp1)
        result = execShell(openssl + " x509 -in " +
                           certPath + " -noout -subject")
        if result[1].find('-bash:') != -1:
            return True
        if len(result[1]) > 2:
            return False
        if result[0].find('error:') != -1:
            return False
    return True


def getPathSize(path):
    # 取文件或目录大小
    if not os.path.exists(path):
        return 0
    if not os.path.isdir(path):
        return os.path.getsize(path)
    size_total = 0
    for nf in os.walk(path):
        for f in nf[2]:
            filename = nf[0] + '/' + f
            size_total += os.path.getsize(filename)
    return size_total


def toSize(size):
    # 字节单位转换
    d = ('b', 'KB', 'MB', 'GB', 'TB')
    s = d[0]
    for b in d:
        if size < 1024:
            return str(round(size, 2)) + ' ' + b
        size = float(size) / 1024.0
        s = b
    return str(round(size, 2)) + ' ' + b


def getMacAddress():
    # 获取mac
    import uuid
    mac = uuid.UUID(int=uuid.getnode()).hex[-12:]
    return ":".join([mac[e:e + 2] for e in range(0, 11, 2)])


def get_string(t):
    if t != -1:
        max = 126
        m_types = [{'m': 122, 'n': 97}, {'m': 90, 'n': 65}, {'m': 57, 'n': 48}, {
            'm': 47, 'n': 32}, {'m': 64, 'n': 58}, {'m': 96, 'n': 91}, {'m': 125, 'n': 123}]
    else:
        max = 256
        t = 0
        m_types = [{'m': 255, 'n': 0}]
    arr = []
    for i in range(max):
        if i < m_types[t]['n'] or i > m_types[t]['m']:
            continue
        arr.append(chr(i))
    return arr


def get_string_find(t):
    if type(t) != list:
        t = [t]
    return_str = ''
    for s1 in t:
        return_str += get_string(int(s1[0]))[int(s1[1:])]
    return return_str


def get_string_arr(t):
    s_arr = {}
    t_arr = []
    for s1 in t:
        for i in range(6):
            if not i in s_arr:
                s_arr[i] = get_string(i)
            for j in range(len(s_arr[i])):
                if s1 == s_arr[i][j]:
                    t_arr.append(str(i) + str(j))
    return t_arr

 # 转换时间


def strfDate(sdate):
    return time.strftime('%Y-%m-%d', time.strptime(sdate, '%Y%m%d%H%M%S'))


# 获取证书名称
def getCertName(certPath):
    if not os.path.exists(certPath):
        return None
    try:
        import OpenSSL
        result = {}
        x509 = OpenSSL.crypto.load_certificate(
            OpenSSL.crypto.FILETYPE_PEM, readFile(certPath))
        # 取产品名称
        issuer = x509.get_issuer()
        result['issuer'] = ''
        if hasattr(issuer, 'CN'):
            result['issuer'] = issuer.CN
        if not result['issuer']:
            is_key = [b'0', '0']
            issue_comp = issuer.get_components()
            if len(issue_comp) == 1:
                is_key = [b'CN', 'CN']
            for iss in issue_comp:
                if iss[0] in is_key:
                    result['issuer'] = iss[1].decode()
                    break
        if not result['issuer']:
            if hasattr(issuer, 'O'):
                result['issuer'] = issuer.O
        # 取到期时间
        result['notAfter'] = strfDate(
            bytes.decode(x509.get_notAfter())[:-1])
        # 取申请时间
        result['notBefore'] = strfDate(
            bytes.decode(x509.get_notBefore())[:-1])
        # 取可选名称
        result['dns'] = []
        for i in range(x509.get_extension_count()):
            s_name = x509.get_extension(i)
            if s_name.get_short_name() in [b'subjectAltName', 'subjectAltName']:
                s_dns = str(s_name).split(',')
                for d in s_dns:
                    result['dns'].append(d.split(':')[1])
        subject = x509.get_subject().get_components()
        # 取主要认证名称
        if len(subject) == 1:
            result['subject'] = subject[0][1].decode()
        else:
            if not result['dns']:
                for sub in subject:
                    if sub[0] == b'CN':
                        result['subject'] = sub[1].decode()
                        break
                if 'subject' in result:
                    result['dns'].append(result['subject'])
            else:
                result['subject'] = result['dns'][0]
        result['endtime'] = int(int(time.mktime(time.strptime(
            result['notAfter'], "%Y-%m-%d")) - time.time()) / 86400)
        return result
    except Exception as e:
        # print(getTracebackInfo())
        return None


def createSSL():
    # 自签证书
    if os.path.exists('ssl/input.pl'):
        return True
    import OpenSSL
    key = OpenSSL.crypto.PKey()
    key.generate_key(OpenSSL.crypto.TYPE_RSA, 2048)
    cert = OpenSSL.crypto.X509()
    cert.set_serial_number(0)
    cert.get_subject().CN = getLocalIp()
    cert.set_issuer(cert.get_subject())
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(86400 * 3650)
    cert.set_pubkey(key)
    cert.sign(key, 'md5')
    cert_ca = OpenSSL.crypto.dump_certificate(
        OpenSSL.crypto.FILETYPE_PEM, cert)
    private_key = OpenSSL.crypto.dump_privatekey(
        OpenSSL.crypto.FILETYPE_PEM, key)
    if len(cert_ca) > 100 and len(private_key) > 100:
        writeFile('ssl/cert.pem', cert_ca, 'wb+')
        writeFile('ssl/private.pem', private_key, 'wb+')
        return True
    return False


def getSSHPort():
    try:
        file = '/etc/ssh/sshd_config'
        conf = readFile(file)
        rep = "(#*)?Port\s+([0-9]+)\s*\n"
        port = re.search(rep, conf).groups(0)[1]
        return int(port)
    except:
        return 22


def getSSHStatus():
    if os.path.exists('/usr/bin/apt-get'):
        status = execShell("service ssh status | grep -P '(dead|stop)'")
    else:
        import system_api
        version = system_api.system_api().getSystemVersion()
        if version.find(' Mac ') != -1:
            return True
        if version.find(' 7.') != -1:
            status = execShell("systemctl status sshd.service | grep 'dead'")
        else:
            status = execShell(
                "/etc/init.d/sshd status | grep -e 'stopped' -e '已停'")
    if len(status[0]) > 3:
        status = False
    else:
        status = True
    return status


def requestFcgiPHP(sock, uri, document_root='/tmp', method='GET', pdata=b''):
    # 直接请求到PHP-FPM
    # version php版本
    # uri 请求uri
    # filename 要执行的php文件
    # args 请求参数
    # method 请求方式
    sys.path.append(os.getcwd() + "/class/plugin")

    import fpm
    p = fpm.fpm(sock, document_root)

    if type(pdata) == dict:
        pdata = url_encode(pdata)
    result = p.load_url_public(uri, pdata, method)
    return result


def getMyORM():
    '''
    获取MySQL资源的ORM
    '''
    sys.path.append(os.getcwd() + "/class/plugin")
    import orm
    o = orm.ORM()
    return o


def getMyORMDb():
    '''
    获取MySQL资源的ORM pip install mysqlclient==2.0.3 | pip install mysql-python
    '''
    sys.path.append(os.getcwd() + "/class/plugin")
    import ormDb
    o = ormDb.ORM()
    return o
