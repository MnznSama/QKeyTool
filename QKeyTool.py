import json
import re
import time
import requests
import urllib3
from urllib.parse import quote
from urllib3.exceptions import InsecureRequestWarning

class QQManager:
    def __init__(self):
        self.session = requests.Session()
        urllib3.disable_warnings(InsecureRequestWarning)
        self.session.verify = False
        self._init_headers()
        self.uin = None
        self.bkn = None

    def _init_headers(self):
        self.session.headers.update({
            'Referer': 'https://xui.ptlogin2.qq.com/'
        })

    def _update_cookies(self, response):
        new_cookies = response.cookies

        for cookie in new_cookies:
            existing = next(
                (c for c in self.session.cookies
                 if c.name == cookie.name
                 and c.domain == cookie.domain
                 and c.path == cookie.path),
                None
            )
            if existing:
                self.session.cookies.clear(existing.domain, existing.path, existing.name)

            self.session.cookies.set_cookie(cookie)

        if new_cookies:
            current = requests.utils.dict_from_cookiejar(new_cookies)

    def get_current_cookies(self):
        return requests.utils.dict_from_cookiejar(self.session.cookies)

    def _get_pt_local_token(self):
        url = "https://xui.ptlogin2.qq.com/cgi-bin/xlogin?s_url=https%3A%2F%2Fhuifu.qq.com%2Findex.html"

        try:
            response = self.session.get(url)
            response.raise_for_status()
            self._update_cookies(response)

            pt_tokens = [c for c in self.session.cookies if c.name == 'pt_local_token']
            if len(pt_tokens) > 1:
                print("Multiple pt_local_token found, using latest")
                for cookie in pt_tokens[:-1]:
                    self.session.cookies.clear(cookie.domain, cookie.path, cookie.name)
            print("Get pt_local_token:", response.cookies.get('pt_local_token') or 'Not found')
            return True
        except requests.exceptions.TooManyRedirects as e:
            raise
        except KeyError:
            raise

    def _get_uin_list(self):
        pt_local_token = self.session.cookies['pt_local_token']
        url = f"https://localhost.ptlogin2.qq.com:4301/pt_get_uins?" \
              f"callback=ptui_getuins_CB&pt_local_tk={quote(pt_local_token)}"

        response = self.session.get(url)
        self._update_cookies(response)

        json_str = response.text.split('=', 1)[1].split(';')[0].strip()
        data = json.loads(json_str)
        return data

    def _get_client_key(self):
        import random
        random.seed(int(time.time()))
        
        for attempt in range(3):
            random_val = random.random()
            url = f"https://localhost.ptlogin2.qq.com:4301/pt_get_st?clientuin={self.uin}&r={random_val}&pt_local_tk={self.session.cookies['pt_local_token']}&callback=__jp{attempt}"

            try:
                response = self.session.get(url)
                self._update_cookies(response)
                
                clientkey = self.session.cookies.get('clientkey')
                
                if clientkey:
                    self.clientkey = clientkey
                    print(f"Get clientkey: {clientkey}")
                    return clientkey
                    
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                
        print("Warning: Failed to get clientkey after all attempts")
                
        return None

    def _calculate_bkn(self):
        skey = self.session.cookies.get('skey', '')

        print("Cookies:")
        for cookie in self.session.cookies:
            print(f"  {cookie.name}: {cookie.value}")

        if not skey:
            raise ValueError("Missing skey in cookies, check login process")

        t = 5381
        for char in skey:
            t += (t << 5) + ord(char)
        self.bkn = str(t & 0x7FFFFFFF)
        print(f"Get BKN: {self.bkn}")

    def _handle_redirect(self, redirect_url):
        response = self.session.get(redirect_url, allow_redirects=True)
        self._update_cookies(response)
        if 'p_skey' not in self.session.cookies:
            raise ValueError("Failed to get p_skey after redirect")
    
    def login(self):
        self._get_pt_local_token()

        accounts = self._get_uin_list()
        
        self.uin = self._select_account(accounts)

        print(f"Use UIN: {self.uin}")

        clientkey = self._get_client_key()
        
        if not clientkey:
            print("Failed to get clientkey, continuing login process...")

        jump_url = f"https://ssl.ptlogin2.qq.com/jump?clientuin={self.uin}&keyindex=19&pt_aid=715030901&daid=73&u1=https%3A%2F%2Fqun.qq.com%2F&pt_local_tk={self.session.cookies['pt_local_token']}&pt_3rd_aid=0&ptopt=1&style=40&has_onekey=1"

        response = self.session.get(jump_url, allow_redirects=False)
        self._update_cookies(response)

        if "'" in response.text:
            url_parts = response.text.split("'")
            if len(url_parts) > 3:
                url = url_parts[3]
                response = self.session.get(url)

        try:
            self._calculate_bkn()
        except ValueError as e:
            print(f"BKN calculation failed: {e}")

    def _select_account(self, accounts):
        if not accounts:
            raise ValueError("No available accounts")
        
        print("Please select an account:")
        print("0. Exit")
        for i, account in enumerate(accounts, 1):
            uin = account.get('uin', 'Unknown')
            print(f"{i}. UIN: {uin}")
        
        while True:
            try:
                choice = input(f"Enter choice (0-{len(accounts)}): ").strip()
                choice_idx = int(choice) - 1
                if choice == '0':
                    print("Exiting...")
                    raise KeyboardInterrupt
                elif 0 <= choice_idx < len(accounts):
                    selected_uin = accounts[choice_idx]['uin']
                    print(f"Selected account: {selected_uin}")
                    return selected_uin
                else:
                    print(f"Please enter a number between 1 and {len(accounts)}")
            except ValueError:
                print("Please enter a valid number")
            except KeyboardInterrupt:
                print("\nSelection cancelled")
                raise

if __name__ == "__main__":
    try:
        qm = QQManager()
        qm.login()

    except requests.exceptions.RequestException as e:
        print(f"Network request failed: {str(e)}")
    except json.JSONDecodeError as e:
        print(f"JSON parsing failed: {str(e)}")
    except ValueError as e:
        print(f"Data processing error: {str(e)}")
    except Exception as e:
        print(f"Unknown error: {str(e)}")
