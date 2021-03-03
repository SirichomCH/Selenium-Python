import time

# from cryptography.fernet import Fernet

from browser import Browser
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import redis
import settings


class KMA:
    BOT = None
    OP = None
    DROPDOWNBANK = {'002': 'bbl',
                    '004': 'kbank',
                    '006': 'ktb',
                    '011': 'tmb',
                    '014': 'scb',
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
        self.BOT.get('https://www.krungsrionline.com/BAY.KOL.WebSite/Common/Login.aspx')
        print("Inputting username")
        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.ID, 'ctl00_cphForLogin_username')))
        txt_username = self.BOT.find_element(By.ID, 'ctl00_cphForLogin_username')
        txt_username.send_keys(self.USERNAME)

        print("Inputting password")
        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.ID, 'ctl00_cphForLogin_password')))
        txt_password = self.BOT.find_element(By.ID, 'ctl00_cphForLogin_password')
        txt_password.send_keys(self.PASSWORD)

        print("Logging in")
        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.ID, 'ctl00_cphForLogin_lbtnLoginNew')))
        btn_login = self.BOT.find_element(By.ID, "ctl00_cphForLogin_lbtnLoginNew")
        btn_login.click()

    def withdrawal(self):
        self.go_to_transfer_page()

        bank = self.OP['to']['bank']['code']
        key = {'key': key for key, value in self.DROPDOWNBANK.items() if value == bank}
        print("Select bank")
        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.ID, 'ddlBanking')))
        selection_bank = Select(self.BOT.find_element(By.ID, 'ddlBanking'))
        selection_bank.select_by_value(key['key'])

        print("Inputting account number")
        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.ID, 'ctl00_cphSectionData_txtAccTo')))
        txt_account_number = self.BOT.find_element(By.ID, 'ctl00_cphSectionData_txtAccTo')
        txt_account_number.send_keys(self.OP['to']['account_number'])

        print("Inputting amount")
        WebDriverWait(self.BOT, 60).until(
            EC.presence_of_element_located((By.ID, 'ctl00_cphSectionData_txtAmountTransfer')))
        txt_amount = self.BOT.find_element(By.ID, 'ctl00_cphSectionData_txtAmountTransfer')
        txt_amount.send_keys(self.OP['op']['amount'])

        print("Submit")
        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.ID, "ctl00_cphSectionData_btnSubmit")))
        btn_next = self.BOT.find_element(By.ID, "ctl00_cphSectionData_btnSubmit")
        btn_next.click()

        # //*[@id="ctl00_cphSectionData_OTPBox1_pnlOTBBOxBody"]/div[2]/div[2]
        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located(
            (By.XPATH, '//*[@id="ctl00_cphSectionData_OTPBox1_pnlOTBBOxBody"]/div[2]/div[2]')))
        txt_reference_code = self.BOT.find_element(By.XPATH,
                                                   '//*[@id="ctl00_cphSectionData_OTPBox1_pnlOTBBOxBody"]/div[2]/div[2]')
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

        print("Waiting OTP")
        WebDriverWait(self.BOT, 60).until(
            EC.presence_of_element_located((By.ID, 'ctl00_cphSectionData_OTPBox1_txtOTPPassword')))
        txt_one_time_password = self.BOT.find_element(By.ID, 'ctl00_cphSectionData_OTPBox1_txtOTPPassword')
        txt_one_time_password.send_keys(one_time_password)

        print("Withdrawal success")
        WebDriverWait(self.BOT, 60).until(
            EC.presence_of_element_located((By.ID, 'ctl00_cphSectionData_OTPBox1_btnConfirm')))
        btn_confirm = self.BOT.find_element(By.ID, 'ctl00_cphSectionData_OTPBox1_btnConfirm')
        btn_confirm.click()

        WebDriverWait(self.BOT, 60).until(
            EC.presence_of_element_located((By.ID, 'ctl00_cphSectionData_imgIconSuccess')))

    def deposit(self):
        print("Check deposit")
        self.go_to_statement_page()
        if self.OP['from']['bank']['code'] == 'kma':
            self.kma_transfer_bank()
        else:
            self.other_transfer_bank()
        # for i in
        # statement_table = self.BOT.find_element(By.CSS_SELECTOR, 'tr')



    def go_to_transfer_page(self):
        print("Go to transfer page")
        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'a[pageid="11"]')))
        link_transfer = self.BOT.find_element(By.CSS_SELECTOR, 'a[pageid="11"]')
        link_transfer.click()

        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.ID, 'ctl00_cphSectionData_rptAccFrom_ctl01_imgCard')))
        AccFrom = self.BOT.find_element(By.ID, 'ctl00_cphSectionData_rptAccFrom_ctl01_imgCard')
        AccFrom.click()

    def go_to_statement_page(self):
        print("Go to statement page")
        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'a[pageid="5"]')))
        link_transaction = self.BOT.find_element(By.CSS_SELECTOR, 'a[pageid="5"]')
        link_transaction.click()

        WebDriverWait(self.BOT, 60).until(EC.presence_of_element_located((By.ID, 'ctl00_cphSectionData_ddlAccountNickName')))
        link_transaction = Select(self.BOT.find_element(By.ID, 'ctl00_cphSectionData_ddlAccountNickName'))
        link_transaction.select_by_value('6669644|1|บอท|7841240921')

        time.sleep(5)

    def kma_transfer_bank(self):
        statement_table_row = self.BOT.find_elements(By.TAG_NAME, 'tr')
        data = []
        for statement_table_row in statement_table_row:
            statement_table_columns = statement_table_row.find_elements(By.TAG_NAME, 'td')
            for statement_table_column in statement_table_columns:
                data.append(statement_table_column.text)
        print(data)
        account_number = self.OP['from']['account_number']
        deposit_amount = self.OP['op']['amount']
        deposit_amount = float(deposit_amount)
        print(deposit_amount)
        result = []
        print("Checking information")
        for i in data:
            if account_number in i:
                index_i = data.index(i)
                index_i = index_i + 2
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
        statement_table_row = self.BOT.find_elements(By.TAG_NAME, 'tr')
        data = []
        for statement_table_row in statement_table_row:
            statement_table_columns = statement_table_row.find_elements(By.TAG_NAME, 'td')
            for statement_table_column in statement_table_columns:
                data.append(statement_table_column.text)
        print(data)
        print("Checking information")
        account_number = self.OP['from']['account_number']
        account_number = account_number[-7:]
        deposit_amount = self.OP['op']['amount']
        deposit_amount = float(deposit_amount)
        print(deposit_amount)
        result = []
        for i in data:
            if account_number in i:
                index_i = data.index(i)
                index_i = index_i + 2
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