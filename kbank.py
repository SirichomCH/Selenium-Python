from browser import Browser
# from cryptography.fernet import Fernet
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import time
import redis
import settings


class KBank:
    BOT = None
    OP = None
    DROPDOWNBANK = {'2': 'bbl',
                    '0': 'kbank',
                    '4': 'ktb',
                    '8': 'tmb',
                    '10': 'scb',
                    '17': 'cimb',
                    '18': 'uob',
                    '19': 'bay',
                    '24': 'gsb',
                    '119': 'baac',
                    '106': 'tbank',
                    '120': 'kkp'}
    USERNAME = None
    PASSWORD = None

    def __init__(self, op):
        self.OP = op
        self.USERNAME = self.OP['from']['bot']['username'] if 'bot' in self.OP['from'] else self.OP['to']['bot']['username']
        self.PASSWORD = self.OP['from']['bot']['password'] if 'bot' in self.OP['from'] else self.OP['to']['bot']['password']
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
        self.BOT.get('https://online.kasikornbankgroup.com/K-Online/')
        print("Inputting username")
        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.NAME, 'userName')))
        txt_username = self.BOT.find_element(By.NAME, 'userName')
        txt_username.send_keys(self.USERNAME)

        print("Inputting password")
        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.NAME, 'password')))
        txt_password = self.BOT.find_element(By.NAME, 'password')
        txt_password.send_keys(self.PASSWORD)

        print("Logging in")
        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.ID, 'loginBtn')))
        btn_login = self.BOT.find_element(By.ID, "loginBtn")
        btn_login.click()

        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.ID, "ssoIFrame1")))
        iframe = self.BOT.find_element(By.ID, "ssoIFrame1")
        self.BOT.switch_to.frame(iframe)

    def withdrawal(self):
        self.add_other_account()
        self.go_to_transfer_page()

        print("Select from account")
        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.NAME, 'fromAccount')))
        selection_from_account = Select(self.BOT.find_element(By.NAME, 'fromAccount'))
        selection_from_account.select_by_value('20201209010094')

        rint("Select to account")
        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.NAME, 'toAccount')))
        selection_to_account = Select(self.BOT.find_element(By.NAME, 'toAccount'))
        for o in selection_to_account.options:
            if '{} {}'.format('-'.join([self.OP['to']['account_number'][:3],
                                        self.OP['to']['account_number'][3:4],
                                        self.OP['to']['account_number'][4:9],
                                        self.OP['to']['account_number'][9:10]]),
                              self.OP['to']['name']) in o.text:
                o.click()

        print("Inputting amount")
        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.NAME, 'creditAmount')))
        txt_credit_amount = self.BOT.find_element(By.NAME, 'creditAmount')
        txt_credit_amount.send_keys(self.OP['op']['amount'])

        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "img[src='/retailstatic/images/button/Next_th.gif']")))
        btn_next = self.BOT.find_element(By.CSS_SELECTOR, "img[src='/retailstatic/images/button/Next_th.gif']")
        btn_next.click()

        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.NAME, 'currentOTPRefNo')))
        txt_reference_code = self.BOT.find_element(By.NAME, 'currentOTPRefNo')
        reference_code = txt_reference_code.get_attribute('value')
        one_time_password = None

        rd_client = redis.Redis(host=settings.REDIS_HOST, password=settings.REDIS_PASSWORD)
        while True:
            if rd_client.exists(reference_code):
                one_time_password = rd_client.get(reference_code).decode('utf-8')
            if one_time_password is not None:
                rd_client.delete(reference_code)
                break
        rd_client.close()

        print("Waiting OTP")
        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.NAME, 'secondaryPassword')))
        txt_one_time_password = self.BOT.find_element(By.NAME, 'secondaryPassword')
        txt_one_time_password.send_keys(one_time_password)

        print("withdrawal success")
        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.NAME, 'btnSubmit')))
        btn_submit = self.BOT.find_element(By.NAME, 'btnSubmit')
        btn_submit.click()

        self.remove_other_account()

    def deposit(self):
        print("Check deposit")
        self.go_to_statement_page()
        if self.OP['from']['bank']['code'] == 'kbank':
            self.kbank_transfer_bank()
        else:
            self.other_transfer_bank()

    def go_to_transfer_page(self):
        print("Go to transfer page")
        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.CSS_SELECTOR, "img#CC")))
        link_transfer = self.BOT.find_element(By.CSS_SELECTOR, 'img#CC')
        if "over" not in link_transfer.get_attribute('src'):
            link_transfer.click()

        if self.OP['to']['bank']['code'] == 'kbank':
            WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.LINK_TEXT, "โอนเงินให้บุคคลอื่น")))
            link_transfer = self.BOT.find_element(By.LINK_TEXT, "โอนเงินให้บุคคลอื่น")
            link_transfer.click()
        else:
            WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.LINK_TEXT, "โอนเงินต่างธนาคาร")))
            link_transfer_other_bank = self.BOT.find_element(By.LINK_TEXT, "โอนเงินต่างธนาคาร")
            link_transfer_other_bank.click()

    def go_to_other_account_page(self):
        print("Go to other account page")
        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.CSS_SELECTOR, "img#GG")))
        link_edit_personal_info = self.BOT.find_element(By.CSS_SELECTOR, 'img#GG')
        if "over" not in link_edit_personal_info.get_attribute('src'):
            link_edit_personal_info.click()

        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.LINK_TEXT, "บัญชีบุคคลอื่น")))
        link_other_accounts = self.BOT.find_element(By.LINK_TEXT, "บัญชีบุคคลอื่น")
        link_other_accounts.click()

    def add_other_account(self):
        self.go_to_other_account_page()

        print("Create new person")
        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, 'img[src="/retailstatic/images/button/AddOtherAccounts_th.gif"]')))
        btn_create_new_person = self.BOT.find_element(By.CSS_SELECTOR,
                                                      'img[src="/retailstatic/images/button/AddOtherAccounts_th.gif"]')
        btn_create_new_person.click()

        bank = self.OP['to']['bank']['code']
        key = {'key': key for key, value in self.DROPDOWNBANK.items() if value == bank}
        print("Select bank")
        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.NAME, 'bankID')))
        selection_bank = Select(self.BOT.find_element(By.NAME, 'bankID'))
        selection_bank.select_by_value(key['key'])

        print("Inputting account number")
        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.NAME, 'accountNumber')))
        txt_account_number = self.BOT.find_element(By.NAME, 'accountNumber')
        txt_account_number.send_keys(self.OP['to']['account_number'])

        print("Inputting name")
        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.NAME, 'accountName')))
        txt_account_name = self.BOT.find_element(By.NAME, 'accountName')
        txt_account_name.send_keys(self.OP['to']['name'])

        print("Submit")
        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "input[src='/retailstatic/images/button/Submit_th.gif'][type='image']")))
        btn_submit = self.BOT.find_element(By.CSS_SELECTOR,
                                           "input[src='/retailstatic/images/button/Submit_th.gif'][type='image']")
        btn_submit.click()

        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.NAME, 'currentOTPRefNo')))
        txt_reference_code = self.BOT.find_element(By.NAME, 'currentOTPRefNo')
        reference_code = txt_reference_code.get_attribute('value')
        one_time_password = None

        rd_client = redis.Redis(host=settings.REDIS_HOST, password=settings.REDIS_PASSWORD)
        while True:
            if rd_client.exists(reference_code):
                one_time_password = rd_client.get(reference_code).decode('utf-8')
            if one_time_password is not None:
                rd_client.delete(reference_code)
                break
        rd_client.close()

        print("Waiting OTP")
        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.NAME, 'secondPassword')))
        txt_one_time_password = self.BOT.find_element(By.NAME, 'secondPassword')
        txt_one_time_password.send_keys(one_time_password)

        print("Create account success")
        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.NAME, 'btnConfirm')))
        btn_submit = self.BOT.find_element(By.NAME, 'btnConfirm')
        btn_submit.click()

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
            select = Select(match_account.find_element(By.XPATH, "..//td[last()]//select"))
            select.select_by_visible_text('ลบ')

            WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.NAME, 'btnDelete')))
            btn_delete = self.BOT.find_element(By.NAME, 'btnDelete')
            btn_delete.click()

            WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.NAME, 'btnReturn')))
            btn_return = self.BOT.find_element(By.NAME, 'btnReturn')
            btn_return.click()
            break

        if len(match_accounts) > 0:
            self.remove_matches_account()

    def go_to_statement_page(self):
        print("Go to statement page")
        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.CSS_SELECTOR, "img#AA")))
        link_statement = self.BOT.find_element(By.CSS_SELECTOR, 'img#AA')
        if "over" not in link_statement.get_attribute('src'):
            link_statement.click()

        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.LINK_TEXT, "รายการเคลื่อนไหวล่าสุด")))
        link_statement = self.BOT.find_element(By.LINK_TEXT, "รายการเคลื่อนไหวล่าสุด")
        link_statement.click()

        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.NAME, 'acctId')))
        link_transaction = Select(self.BOT.find_element(By.NAME, 'acctId'))
        link_transaction.select_by_value('20201209010094')

        time.sleep(5)

    def kbank_transfer_bank(self):
        statement_table = self.BOT.find_element(By.ID, 'trans_detail')
        statement_table_rows = statement_table.find_elements(By.TAG_NAME, 'tr')
        data = []
        for statement_table_row in statement_table_rows:
            statement_table_columns = statement_table_row.find_elements(By.TAG_NAME, 'td')
            for statement_table_column in statement_table_columns:
                data.append(statement_table_column.text)
        print(data)
        account_number = self.OP['from']['account_number']
        deposit_amount = self.OP['op']['amount']
        deposit_amount = float(deposit_amount)
        print(deposit_amount)
        print("Checking information")
        result = []
        for i in data:
            if "ฝากด้วยเช็คธนาคาร/โอน" in i:
                index_i = data.index(i)
                index_i = index_i + 3
                bankaccount = data[index_i]
                bankaccount = bankaccount.replace("-", "")
                bankaccount = bankaccount.replace("x", "")
                if bankaccount in account_number:
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
        pass
