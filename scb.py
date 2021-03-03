import time

# from cryptography.fernet import Fernet
from browser import Browser
from pytesseract import Output
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import cv2
import os
import pytesseract
import redis
import settings
import urllib.request


class SCB:
    BOT = None
    OP = None
    CORDS = {
        0: {'x': 12, 'y': 12},
        1: {'x': 12, 'y': 40},
        2: {'x': 12, 'y': 68},
        3: {'x': 12, 'y': 96},
        4: {'x': 12, 'y': 124},
        5: {'x': 42, 'y': 12},
        6: {'x': 42, 'y': 40},
        7: {'x': 42, 'y': 68},
        8: {'x': 42, 'y': 96},
        9: {'x': 42, 'y': 124},
    }
    DROPDOWNBANK = {'002': 'bbl',
                    '004': 'kbank',
                    '006': 'ktb',
                    '011': 'tmb',
                    '022': 'cimb',
                    '024': 'uob',
                    '025': 'bay',
                    '030': 'gsb',
                    '034': 'baac',
                    '065': 'tbank',
                    '069': 'kkp'}

    def __init__(self, op):
        self.OP = op
        self.USERNAME = self.OP['from']['bot']['username'] if 'bot' in self.OP['from'] else self.OP['to']['bot'][
            'username']
        self.PASSWORD = self.OP['from']['bot']['password'] if 'bot' in self.OP['from'] else self.OP['to']['bot'][
            'password']
        f = Fernet(str.encode(settings.APP_KEY))
        self.PASSWORD = f.decrypt(str.encode(self.PASSWORD)).decode("utf-8")

    def run(self):
        self.create_browser()
        self.login()
        self.withdrawal() if self.OP['op']['type'] == 'withdrawal' else self.deposit()
        self.BOT.quit()

    def create_browser(self):
        print("Open browser")
        self.BOT = Browser().create()

    def login(self):
        self.BOT.get('https://www.scbeasy.com/v1.4/site/presignon/index.asp')
        print("Inputting username")
        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.NAME, 'LOGIN')))
        txt_username = self.BOT.find_element(By.NAME, 'LOGIN')
        txt_username.send_keys(self.USERNAME)

        print("Inputting password")
        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.NAME, 'PASSWD')))
        txt_password = self.BOT.find_element(By.NAME, 'PASSWD')
        txt_password.send_keys(self.PASSWORD)

        print("Logging in")
        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.NAME, 'lgin')))
        btn_login = self.BOT.find_element(By.ID, "lgin")
        btn_login.click()

        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.NAME, 'Image3')))
        link_account_page = self.BOT.find_element(By.ID, "Image3")
        link_account_page.click()

    def withdrawal(self):
        self.add_other_account()
        self.go_to_transfer_page()

        print("Select to account")
        if self.OP['to']['bank']['code'] == 'scb':
            WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.ID, 'DataProcess_ddlCustAccTo')))
            selection_to_account = Select(self.BOT.find_element(By.ID, 'DataProcess_ddlCustAccTo'))
        else:
            WebDriverWait(self.BOT, 60).until(
                EC.presence_of_element_located((By.ID, 'DataProcess_CustReceiveAccountOtherBank_DropDownList')))
            selection_to_account = Select(
                self.BOT.find_element(By.ID, 'DataProcess_CustReceiveAccountOtherBank_DropDownList'))
        for o in selection_to_account.options:
            if '{} - {}'.format(self.OP['to']['name'],
                                self.OP['to']['account_number']) in o.text:
                o.click()

        print("Inputting amount")
        if self.OP['to']['bank']['code'] == 'scb':
            WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.ID, 'DataProcess_txtCustAmount')))
            txt_amount = self.BOT.find_element(By.ID, 'DataProcess_txtCustAmount')
        else:
            WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.ID, 'DataProcess_CustAmount_TextBox')))
            txt_amount = self.BOT.find_element(By.ID, 'DataProcess_CustAmount_TextBox')
        txt_amount.send_keys(self.OP['op']['amount'])

        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.ID, "DataProcess_Next_LinkButton")))
        btn_next = self.BOT.find_element(By.ID, "DataProcess_Next_LinkButton")
        btn_next.click()

        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.ID, "nxt")))
        btn_next = self.BOT.find_element(By.ID, "nxt")
        btn_next.click()

        print("Waiting OTP")
        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.ID, 'DataProcess_lbOTPRefNo')))
        txt_reference_code = self.BOT.find_element(By.ID, 'DataProcess_lbOTPRefNo')
        reference_code = txt_reference_code.text
        one_time_password = None

        rd_client = redis.Redis(host=settings.REDIS_HOST, password=settings.REDIS_PASSWORD)
        while True:
            if rd_client.exists(reference_code):
                one_time_password = rd_client.get(reference_code).decode('utf-8')
            if one_time_password is not None:
                rd_client.delete(reference_code)
                break
        rd_client.close()

        self.BOT.execute_script("window.open('');")
        self.BOT.switch_to.window(self.BOT.window_handles[1])
        self.BOT.get('https://www.scbeasy.com/online/easynet/page/DynamicPinpad.aspx')
        pad_image = self.BOT.find_element(By.CSS_SELECTOR, 'body > img')
        pad_image_src = pad_image.get_attribute('src')
        cookies = self.BOT.get_cookies()
        session = None
        for cookie in cookies:
            if cookie['name'] == 'SESSIONEASY':
                session = cookie['value']
        opener = urllib.request.build_opener()
        opener.addheaders = [('Cookie', 'SESSIONEASY={}'.format(session))]
        urllib.request.install_opener(opener)
        urllib.request.urlretrieve(pad_image_src, 'pin_pad.png')
        self.BOT.close()
        self.BOT.switch_to.window(self.BOT.window_handles[0])
        numbers = []
        for k, cord in self.CORDS.items():
            img = cv2.imread('pin_pad.png', 1)
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            cl = clahe.apply(l)
            limg = cv2.merge((cl, a, b))
            final = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
            image = final[cord['x']:cord['x'] + 15, cord['y']:cord['y'] + 15]
            gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789'
            details = pytesseract.image_to_data(gray_image, output_type=Output.DICT, config=custom_config, lang='eng')
            last_word = ''
            for word in details['text']:
                if word != '':
                    last_word = word
                if (last_word != '' and word == '') or (word == details['text'][-1]):
                    numbers.append('1') if '1' in word and '4' in word else numbers.append(word)

        for char in one_time_password:
            index = numbers.index(char)
            self.BOT.execute_script("DynamicPinpad_Add({});".format(index))

        if os.path.exists("pin_pad.png"):
            os.remove("pin_pad.png")

        print("Withdrawal succes")
        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.ID, 'cnfrm')))
        btn_confirm = self.BOT.find_element(By.ID, 'cnfrm')
        btn_confirm.click()

        self.remove_other_account()

    def deposit(self):
        print("Check deposit")
        self.go_to_statement_page()
        if self.OP['from']['bank']['code'] == 'scb':
            self.scb_transfer_bank()
        else:
            self.other_transfer_bank()

    def go_to_transfer_page(self):
        print("Go to transfer page")
        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.ID, "FundTransfer_Image")))
        link_transfer = self.BOT.find_element(By.ID, 'FundTransfer_Image')
        link_transfer.click()

        if self.OP['to']['bank']['code'] == 'scb':
            print("Go to transfer to other SCB page")
            WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.LINK_TEXT, "บัญชีบุคคลอื่นใน SCB")))
            link_transfer = self.BOT.find_element(By.LINK_TEXT, "บัญชีบุคคลอื่นใน SCB")
            link_transfer.click()
        else:
            print("Go to transfer to other bank page")
            WebDriverWait(self.BOT, 60).until(
                EC.presence_of_element_located((By.LINK_TEXT, "บัญชีบุคคลอื่นต่างธนาคาร")))
            link_transfer_other_bank = self.BOT.find_element(By.LINK_TEXT, "บัญชีบุคคลอื่นต่างธนาคาร")
            link_transfer_other_bank.click()

    def go_to_other_account_page(self):
        print("Go to manage and account setting ")
        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.ID, "EditProfile_Image")))
        link_manage_account_and_setting = self.BOT.find_element(By.ID, 'EditProfile_Image')
        link_manage_account_and_setting.click()

        print("manage account")
        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.LINK_TEXT, "เพิ่ม/ลด/เปิด/ปิดบัญชี")))
        link_manage_accounts = self.BOT.find_element(By.LINK_TEXT, "เพิ่ม/ลด/เปิด/ปิดบัญชี")
        link_manage_accounts.click()

        if self.OP['to']['bank']['code'] == 'scb':
            WebDriverWait(self.BOT, 60).until(
                EC.presence_of_element_located((By.ID, "DataProcess_ctl00_TrdAccount_LinkButton")))
            link_manage_3rd_party_accounts = self.BOT.find_element(By.ID, "DataProcess_ctl00_TrdAccount_LinkButton")
            link_manage_3rd_party_accounts.click()
        else:
            WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.LINK_TEXT, "Another Bank’s Account")))
            link_manage_other_accounts = self.BOT.find_element(By.LINK_TEXT, "Another Bank’s Account")
            link_manage_other_accounts.click()

    def add_other_account(self):
        self.remove_other_account()

        print("Add other account")
        print("Inputting account number")
        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.ID, 'DataProcess_txtCustAccNo')))
        txt_account_number = self.BOT.find_element(By.ID, 'DataProcess_txtCustAccNo')
        txt_account_number.send_keys(self.OP['to']['account_number'])

        if self.OP['to']['bank']['code'] != 'scb':
            bank = self.OP['to']['bank']['code']
            key = {'key': key for key, value in self.DROPDOWNBANK.items() if value == bank}
            print("Select bank")
            WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.ID, 'DataProcess_ddlCustBank')))
            selection_bank = Select(self.BOT.find_element(By.ID, 'DataProcess_ddlCustBank'))
            selection_bank.select_by_value(key['key'])

        print("Inputting name")
        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.ID, 'DataProcess_txtCustAccNickname')))
        txt_account_name = self.BOT.find_element(By.ID, 'DataProcess_txtCustAccNickname')
        txt_account_name.send_keys(self.OP['to']['name'])

        print("Add account")
        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.ID, "add")))
        btn_add = self.BOT.find_element(By.ID, "add")
        btn_add.click()

        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.ID, "cnfrm")))
        btn_confirm = self.BOT.find_element(By.ID, "cnfrm")
        btn_confirm.click()

        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.ID, "ok")))
        btn_ok = self.BOT.find_element(By.ID, "ok")
        btn_ok.click()

        print("Waiting OTP")
        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.ID, 'DataProcess_lbOTPRefNo')))
        txt_reference_code = self.BOT.find_element(By.ID, 'DataProcess_lbOTPRefNo')
        reference_code = txt_reference_code.text
        one_time_password = None

        rd_client = redis.Redis(host=settings.REDIS_HOST, password=settings.REDIS_PASSWORD)
        while True:
            if rd_client.exists(reference_code):
                one_time_password = rd_client.get(reference_code).decode('utf-8')
            if one_time_password is not None:
                rd_client.delete(reference_code)
                break
        rd_client.close()

        self.BOT.execute_script("window.open('');")
        self.BOT.switch_to.window(self.BOT.window_handles[1])
        self.BOT.get('https://www.scbeasy.com/online/easynet/page/DynamicPinpad.aspx')
        pad_image = self.BOT.find_element(By.CSS_SELECTOR, 'body > img')
        pad_image_src = pad_image.get_attribute('src')
        cookies = self.BOT.get_cookies()
        session = None
        for cookie in cookies:
            if cookie['name'] == 'SESSIONEASY':
                session = cookie['value']
        opener = urllib.request.build_opener()
        opener.addheaders = [('Cookie', 'SESSIONEASY={}'.format(session))]
        urllib.request.install_opener(opener)
        urllib.request.urlretrieve(pad_image_src, 'pin_pad.png')
        self.BOT.close()
        self.BOT.switch_to.window(self.BOT.window_handles[0])
        numbers = []
        for k, cord in self.CORDS.items():
            img = cv2.imread('pin_pad.png', 1)
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            cl = clahe.apply(l)
            limg = cv2.merge((cl, a, b))
            final = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
            image = final[cord['x']:cord['x'] + 15, cord['y']:cord['y'] + 15]
            gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789'
            details = pytesseract.image_to_data(gray_image, output_type=Output.DICT, config=custom_config, lang='eng')
            last_word = ''
            for word in details['text']:
                if word != '':
                    last_word = word
                if (last_word != '' and word == '') or (word == details['text'][-1]):
                    numbers.append('1') if '1' in word and '4' in word else numbers.append(word)

        for char in one_time_password:
            index = numbers.index(char)
            self.BOT.execute_script("DynamicPinpad_Add({});".format(index))

        if os.path.exists("pin_pad.png"):
            os.remove("pin_pad.png")

        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.ID, 'DataProcess_Activate_LinkButton')))
        WebDriverWait(self.BOT, 60).until(EC.element_to_be_clickable((By.ID, 'DataProcess_Activate_LinkButton')))
        btn_activate = self.BOT.find_element(By.ID, 'DataProcess_Activate_LinkButton')
        btn_activate.click()
        print("Add other account success")

    def remove_other_account(self):
        print("Remove other account")
        self.go_to_other_account_page()
        self.remove_matches_account()

    def remove_matches_account(self):
        match_accounts = self.BOT.find_elements(By.XPATH,
                                                "//*[contains(text(), '{}')]".format(
                                                    self.OP['to']['name']))
        if len(match_accounts) == 0:
            return True
        for match_account in match_accounts:
            WebDriverWait(match_account, 60).until(EC.presence_of_element_located((By.XPATH, "..//td[last()]//a")))
            link_remove_account = match_account.find_element(By.XPATH, "..//td[last()]//a")
            link_remove_account.click()

            WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.ID, 'cnfrm')))
            btn_confirm = self.BOT.find_element(By.ID, 'cnfrm')
            btn_confirm.click()

            WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.ID, 'ok')))
            btn_ok = self.BOT.find_element(By.ID, 'ok')
            btn_ok.click()
            break

        if len(match_accounts) > 0:
            self.remove_matches_account()

    def go_to_statement_page(self):
        print("Go to statement page")
        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.ID, "DataProcess_SaCaGridView_SaCaView_LinkButton_1")))
        link_view = self.BOT.find_element(By.ID, 'DataProcess_SaCaGridView_SaCaView_LinkButton_1')
        link_view.click()

        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.ID, "DataProcess_Link2")))
        link_todaystatement = self.BOT.find_element(By.ID, 'DataProcess_Link2')
        link_todaystatement.click()
        time.sleep(5)

    def scb_transfer_bank(self):
        statement_table = self.BOT.find_element(By.ID, 'DataProcess_GridView')
        statement_table_rows = statement_table.find_elements(By.TAG_NAME, 'tr')
        data = []
        for statement_table_row in statement_table_rows:
            statement_table_columns = statement_table_row.find_elements(By.TAG_NAME, 'td')
            for statement_table_column in statement_table_columns:
                data.append(statement_table_column.text)
        print(data)
        account_number = self.OP['from']['account_number']
        account_number = "x" + account_number[-4:]
        account_name = self.OP['from']['name']
        account_name = account_name.replace(" ", "")
        deposit_amount = self.OP['op']['amount']
        deposit_amount = float(deposit_amount)
        print(deposit_amount)
        print("Checking information")
        result = []
        for i in data:
            if "รับโอนจาก" in i:
                if account_number in i:
                    j = i[24:]
                    j = j.replace(" ", "")
                    if j in account_name:
                        index_i = data.index(i)
                        index_i = index_i - 1
                        amount = float(data[index_i])
                        print(amount)
                        if amount == deposit_amount:
                            result.append(True)
            else:
                result.append(False)
        if result.__contains__(True):
            print("detected")
        else:
            print("undetected")

    def other_transfer_bank(self):
        statement_table = self.BOT.find_element(By.ID, 'DataProcess_GridView')
        statement_table_rows = statement_table.find_elements(By.TAG_NAME, 'tr')
        data = []
        for statement_table_row in statement_table_rows:
            statement_table_columns = statement_table_row.find_elements(By.TAG_NAME, 'td')
            for statement_table_column in statement_table_columns:
                data.append(statement_table_column.text)

        print(data)
        account_number = self.OP['from']['account_number']
        account_number = "/X" + account_number[-6:]
        deposit_amount = self.OP['op']['amount']
        deposit_amount = float(deposit_amount)
        print(deposit_amount)
        print("Checking information")
        result = []
        for i in data:
            if "รับโอนจาก" not in i:
                if "โอนไป" not in i:
                    if account_number in i:
                        index_i = data.index(i)
                        index_i = index_i - 1
                        amount = float(data[index_i])
                        print(amount)
                        if amount == deposit_amount:
                            result.append(True)
            else:
                result.append(False)
        if result.__contains__(True):
            print("detected")
        else:
            print("undetected")


