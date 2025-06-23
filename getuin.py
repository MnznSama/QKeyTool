import requests
import json
import re

s = requests.Session()

def get_qq_list() -> list:

    URL = f"https://localhost.ptlogin2.qq.com:4301/pt_get_uins?callback=pt_getuins_CB&pt_local_tk=114514"
    response = s.get(URL, cookies={"pt_local_token": "114514"}, headers={"referer": "https://xui.ptlogin2.qq.com/"})
    match = re.search(r'var_sso_uin_list=(\[.*?\]);', response.text)
    if match:
        data_json = match.group(1)
        data_list = json.loads(data_json)

        result = []
        for entry in data_list:
            uin = entry.get("uin")
            nickname = entry.get("nickname")
            result.append({"uin": uin, "nickname": nickname})

        return result
    else:
        print("No matching UIN data found.")
        exit(1)

uin_list = get_qq_list()

for uin in uin_list:
    print(f"UIN: {uin['uin']}, Nickname: {uin['nickname']}")