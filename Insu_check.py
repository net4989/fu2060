# import sys
# from PyQt5.QtWidgets import *







class Insu:
    def __init__(self, haga_pass_items, output_option_data, stock_have_total_money_1per_point, Buy_Item_Max_Cnt):
        # 수신받은 콜/풋 최근 변경 데이터
        self.haga_pass_items = haga_pass_items
        self.output_option_data = output_option_data
        # put_Delta_sum을 구하기 위한 기준 :: # 현재의 보유종목 평가금액
        self.stock_have_total_money_1per_point_90 = stock_have_total_money_1per_point * 0.8
        self.stock_have_total_money_1per_point_110 = stock_have_total_money_1per_point * 1.0
        # print(Delta_sum_ref)
        # print(self.stock_have_total_money_1per_point_90)
        # print(self.stock_have_total_money_1per_point_110)
        # 1회 최대 매수목록
        self.Buy_Item_Max_Cnt = Buy_Item_Max_Cnt

    def insu_check(self):
        # 변수선언
        item_list_cnt = {'code_no': [], 'cnt': []}
        insu_price_sum = 0
        for p in range(len(self.haga_pass_items)):
            for i in range(len(self.output_option_data['code'])):
                if self.haga_pass_items[p] == self.output_option_data['code'][i]:
                        item_cnt = 0
                        insu_price_sum_fu = insu_price_sum + self.output_option_data['run_price'][i]
                        while (insu_price_sum < self.stock_have_total_money_1per_point_90) and (insu_price_sum_fu < self.stock_have_total_money_1per_point_110):
                            insu_price_sum += self.output_option_data['run_price'][i]
                            insu_price_sum_fu = insu_price_sum + self.output_option_data['run_price'][i]
                            item_cnt += 1
                        if item_cnt != 0:
                            item_list_cnt['code_no'].append(self.haga_pass_items[p])
                            item_list_cnt['cnt'].append(item_cnt)
            # print(insu_price_sum)

        # 동일옵션 > Buy_Item_Max_Cnt
        same_option_bic = True
        for i in range(len(item_list_cnt['cnt'])):
            if item_list_cnt['cnt'][i] >= self.Buy_Item_Max_Cnt:
                same_option_bic = False

        if (self.stock_have_total_money_1per_point_90 < insu_price_sum < self.stock_have_total_money_1per_point_110) and (same_option_bic == True):
            return item_list_cnt
        else:
            # 다시검색
            # 검색된 종목건수에서 1을 빼서 다시 검색을 시도한다.
            if len(item_list_cnt['cnt']) != 0:
                for i in range(item_list_cnt['cnt'][0], 0, -1):
                    # 다시검색 함수(처음으로 더한 종목코드 건수 보다 하나적게 더해보기)
                    item_list_cnt = self.insu_check_re(i)
                    # 다시검색 함수에서 구한값 리턴
                    if item_list_cnt != None:
                        return item_list_cnt

            # 변수선언
            item_list_cnt = {'code_no': [], 'cnt': []}
            return item_list_cnt

    def insu_check_re(self, first_cnt):
        # 변수선언
        item_list_cnt = {'code_no': [], 'cnt': []}
        insu_price_sum = 0
        for p in range(len(self.haga_pass_items)):
            for i in range(len(self.output_option_data['code'])):
                if self.haga_pass_items[p] == self.output_option_data['code'][i]:
                    item_cnt = 0
                    insu_price_sum_fu = insu_price_sum + self.output_option_data['run_price'][i]
                    while (insu_price_sum < self.stock_have_total_money_1per_point_90) and (insu_price_sum_fu < self.stock_have_total_money_1per_point_110) and (first_cnt > item_cnt):
                        insu_price_sum += self.output_option_data['run_price'][i]
                        insu_price_sum_fu = insu_price_sum + self.output_option_data['run_price'][i]
                        item_cnt += 1
                    if item_cnt != 0:
                        item_list_cnt['code_no'].append(self.haga_pass_items[p])
                        item_list_cnt['cnt'].append(item_cnt)
            if p == 0:
                first_cnt = 255
            # print(insu_price_sum)

        # 동일옵션 > Buy_Item_Max_Cnt
        same_option_bic = True
        for i in range(len(item_list_cnt['cnt'])):
            if item_list_cnt['cnt'][i] >= self.Buy_Item_Max_Cnt:
                same_option_bic = False

        if (self.stock_have_total_money_1per_point_90 < insu_price_sum < self.stock_have_total_money_1per_point_110) and (same_option_bic == True):
            return item_list_cnt

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # put_insu = Insu
    put_insu = Insu(haga_pass_items_put, self.output_put_option_data, stock_have_total_money_1per_point,
                    Buy_Item_Max_Cnt)
    put_item_list_cnt = put_insu.insu_check()
    print(put_item_list_cnt)
