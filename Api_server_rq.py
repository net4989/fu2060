import sys
import time
from PyQt5.QtWidgets import *
from PyQt5.QAxContainer import *
from PyQt5.QtCore import *











class Kiwoom(QAxWidget):
    def __init__(self):
        super().__init__()
        self._create_kiwoom_instance()
        # self._set_signal_slots()

    # KHOPENAPI 임포트
    def _create_kiwoom_instance(self):
        self.setControl("KHOPENAPI.KHOpenAPICtrl.1")

## 로그인
    # 로그인창 출력
    def comm_connect(self):
        self.dynamicCall("CommConnect()")
        self.login_event_loop = QEventLoop()
        self.login_event_loop.exec_()

    # 로그인 상태처리
    def _event_connect(self, err_code):
        if err_code == 0:
            print("Login_Success")
        else:
            print("Login_Fail")
        self.login_event_loop.exit()

    # 로그인 후 사용
    def get_login_info(self, tag):
        ret = self.dynamicCall("GetLoginInfo(QString)", tag)
        return ret

    #  현재 로그인 상태를 알려줍니다.
    def get_connect_state(self):
        ret = self.dynamicCall("GetConnectState()")
        return ret

## 종목정보관련함수 모음
    def get_code_list_by_market(self, market):
        code_list = self.dynamicCall("GetCodeListByMarket(QString)", market)
        code_list = code_list.split(';')
        return code_list[:-1]

    def get_master_code_name(self, code):
        code_name = self.dynamicCall("GetMasterCodeName(QString)", code)
        return code_name

    def get_option_code(self, strActPrice, nCp, strMonth):
        code_name = self.dynamicCall("GetOptionCode(QString, int, QString)", strActPrice, nCp, strMonth)
        return code_name

    def get_month_mall(self, pickup_no):
        month_raw = self.dynamicCall("GetMonthList()")
        month_list = month_raw.split(";")
        month_mall_cnt = len(month_list)
        month_mall_cnt_half = int(month_mall_cnt / 2)
        month_mall_choice = month_list[month_mall_cnt_half + pickup_no]
        return month_mall_choice

    # [GetFutureList() 함수]
    # 지수선물 종목코드 리스트를 ';'로 구분해서 전달합니다.
    def get_future_s_list(self):
        future_s_list_raw = self.dynamicCall("GetFutureList()")
        future_s_list = future_s_list_raw.split(";")
        return future_s_list

    # [GetOptionATM() 함수]
    # 지수옵션 소수점을 제거한 ATM값을 전달합니다.
    # 예를들어 ATM값이 247.50 인 경우 24750이 전달됩니다.
    # 로그인 한 후에 사용할 수 있는 함수입니다.
    def get_option_s_atm(self):
        get_option_s_atm = self.dynamicCall("GetOptionATM()")
        return get_option_s_atm

















    # OnReceiveTrData 이벤트가 발생할 때 수신 데이터를 가져오는 함수인 _opw00001를 Kiwoom 클래스에 추가
    def _opw00001(self, rqname, trcode):
        d2_deposit = self._comm_get_data(trcode, "", rqname, 0, "d+2추정예수금")
        self.d2_deposit = Kiwoom.change_format(d2_deposit)

    # 총매입금액, 총평가금액, 총평가손익금액, 총수익률, 추정예탁자산을 _comm_get_data 메서드를 통해 얻어옵
    def _opw00018(self, rqname, trcode):
        # single data
        total_purchase_price = self._comm_get_data(trcode, "", rqname, 0, "총매입금액")
        total_eval_price = self._comm_get_data(trcode, "", rqname, 0, "총평가금액")
        total_eval_profit_loss_price = self._comm_get_data(trcode, "", rqname, 0, "총평가손익금액")
        total_earning_rate = self._comm_get_data(trcode, "", rqname, 0, "총수익률(%)")
        estimated_deposit = self._comm_get_data(trcode, "", rqname, 0, "추정예탁자산")

        self.output['single'].append(Kiwoom.change_format(total_purchase_price))
        self.output['single'].append(Kiwoom.change_format(total_eval_price))
        self.output['single'].append(Kiwoom.change_format(total_eval_profit_loss_price))
        # self.opw00018_output['single'].append(Kiwoom.change_format2(total_earning_rate))
        total_earning_rate = Kiwoom.change_format2(total_earning_rate)
        if self.get_server_gubun():
            total_earning_rate = float(total_earning_rate) / 100
            total_earning_rate = str(total_earning_rate)
        self.output['single'].append(total_earning_rate)
        self.output['single'].append(Kiwoom.change_format(estimated_deposit))

        # multi data
        rows = self._get_repeat_cnt(trcode, rqname)
        for i in range(rows):
            name = self._comm_get_data(trcode, "", rqname, i, "종목명")
            quantity = self._comm_get_data(trcode, "", rqname, i, "보유수량")
            purchase_price = self._comm_get_data(trcode, "", rqname, i, "매입가")
            current_price = self._comm_get_data(trcode, "", rqname, i, "현재가")
            eval_profit_loss_price = self._comm_get_data(trcode, "", rqname, i, "평가손익")
            earning_rate = self._comm_get_data(trcode, "", rqname, i, "수익률(%)")

            quantity = Kiwoom.change_format(quantity)
            purchase_price = Kiwoom.change_format(purchase_price)
            current_price = Kiwoom.change_format(current_price)
            eval_profit_loss_price = Kiwoom.change_format(eval_profit_loss_price)
            earning_rate = Kiwoom.change_format2(earning_rate)

            self.output['multi'].append([name, quantity, purchase_price, current_price,
                                                  eval_profit_loss_price, earning_rate])





    def _opt10081(self, rqname, trcode):
        data_cnt = self._get_repeat_cnt(trcode, rqname)

        for i in range(data_cnt):
            date = self._comm_get_data(trcode, "", rqname, i, "일자")
            open = self._comm_get_data(trcode, "", rqname, i, "시가")
            high = self._comm_get_data(trcode, "", rqname, i, "고가")
            low = self._comm_get_data(trcode, "", rqname, i, "저가")
            close = self._comm_get_data(trcode, "", rqname, i, "현재가")
            volume = self._comm_get_data(trcode, "", rqname, i, "거래량")

            self.ohlcv['date'].append(date)
            self.ohlcv['open'].append(int(open))
            self.ohlcv['high'].append(int(high))
            self.ohlcv['low'].append(int(low))
            self.ohlcv['close'].append(int(close))
            self.ohlcv['volume'].append(int(volume))




## 주문
    # Kiwoom 클래스에 send_order 메서드를 추가
    def send_order(self, sRQName, sScreenNo, accountrunVar, CodeCallPut, IOrdKind, sslbyTp, sOrdTp, volumeVar, Price, sOrgOrdNo):
        MarketOrderVar = self.dynamicCall("SendOrderFO(QString, QString, QString, QString, int, QString, QString, int, float, QString)",
                         [sRQName, sScreenNo, accountrunVar, CodeCallPut, IOrdKind, sslbyTp, sOrdTp, volumeVar, Price, sOrgOrdNo])

        # if MarketOrderVar == 0:
        #     print(MarketOrderVar)
        #     # + "주문성공")
        # else:
        #     print(MarketOrderVar)
        #     # + "주문실패")

        return MarketOrderVar

    # Kiwoom 클래스에 send_order_stock 메서드를 추가
    def send_order_stock(self, sRQName, sScreenNo, accountrunVar, IOrdKind, CodeStock, volumeVar, Price, sHogaGb, sOrgOrdNo_cell):
        MarketOrderVar = self.dynamicCall("SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
                         [sRQName, sScreenNo, accountrunVar, IOrdKind, CodeStock, volumeVar, Price, sHogaGb, sOrgOrdNo_cell])

        # if MarketOrderVar == 0:
        #     print(MarketOrderVar)
        #     # + "주문성공")
        # else:
        #     print(MarketOrderVar)
        #     # + "주문실패")

        return MarketOrderVar

    # 체결잔고 데이터를 가져오는 메서드인 GetChejanData를 사용하는 get_chejan_data 메서드를 Kiwoom 클래스에 추가
    def get_chejan_data(self, fid):
        ret = self.dynamicCall("GetChejanData(int)", fid)
        return ret

    #  OnReceiveChejanData 이벤트가 발생할 때 호출되는 _receive_chejan_data는 다음과 같이 구현
    def _receive_chejan_data(self, gubun, item_cnt, fid_list):
        print(gubun)
        print(self.get_chejan_data(9203))
        print(self.get_chejan_data(302))
        print(self.get_chejan_data(900))
        print(self.get_chejan_data(901))




## 서버구분
    # 실 서버에서 수익률은 소수점 표시 없이 전달되지만 모의투자에서는 소수점을 포함해서 데이터가 전달됩니다. 따라서 접속 서버를 구분해서 데이터를 다르게 처리할 필요
    def get_server_gubun(self):
        ret = self.dynamicCall("KOA_Functions(QString, QString)", "GetServerGubun", "")
        return ret





## 숫자 포맷
    # 정적 메서드(static method)를 추가합니다. change_format 메서드는 입력된 문자열에 대해 lstrip 메서드를 통해 문자열 왼쪽에 존재하는 '-' 또는 '0'을 제거합니다. 그리고 format 함수를 통해 천의 자리마다 콤마를 추가한 문자열로 변경
    @staticmethod
    def change_format(data):
        strip_data = data.lstrip('-0')
        if strip_data == '':
            strip_data = '0'

        format_data = format(int(strip_data), ',d')
        if data.startswith('-'):
            format_data = '-' + format_data

        return format_data

    # 수익률에 대한 포맷 변경은 change_format2라는 정적 메서드를 사용
    @staticmethod
    def change_format2(data):
        strip_data = data.lstrip('-0')

        if strip_data == '':
            strip_data = '0'

        if strip_data.startswith('.'):
            strip_data = '0' + strip_data

        if data.startswith('-'):
            strip_data = '-' + strip_data

        return strip_data


if __name__ == "__main__":
    app = QApplication(sys.argv)
    kiwoom = Kiwoom()

    # 로그인창 출력
    kiwoom.comm_connect()


    # print(kiwoom.get_month_mall(0))
    # print(kiwoom.get_month_mall(1))
    # print(kiwoom.get_month_mall(2))
    # print(kiwoom.get_month_mall(3))
    #
    # sID = "만기년월"
    # sValue = kiwoom.get_month_mall(0)
    # sRQName = "콜종목결제월별시세요청"
    # sTrCode = "OPT50021"
    # nPrevNext = "0"
    # sScreenNo = "0021"
    #
    # kiwoom.set_input_value(sID, sValue)
    # kiwoom.comm_rq_data(sRQName,  sTrCode, nPrevNext, sScreenNo)

    # print(TR_REQ_TIME_INTERVAL)

    account_number = kiwoom.get_login_info("ACCNO")
    account_number = account_number.split(';')[0]

    kiwoom.set_input_value("계좌번호", account_number)
    kiwoom.comm_rq_data("opw00018_req", "opw00018", 0, "2000")

    # print(kiwoom.d2_deposit)



