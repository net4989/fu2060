# import sys
# from PyQt5.QtWidgets import *







class Step_Runprice_Delta:
    def __init__(self, haga_pass_items, db_option_pickup, Delta_sum_ref, Buy_Item_Max_Cnt):
        # 수신받은 콜/풋 최근 변경 데이터
        self.haga_pass_items = haga_pass_items
        self.db_option_pickup = db_option_pickup
        # put_Delta_sum을 구하기 위한 기준 :: # 현재의 보유종목 평가금액
        self.Delta_sum_ref_90 = Delta_sum_ref * 0.9
        self.Delta_sum_ref_110 = Delta_sum_ref * 1.1
        # print(Delta_sum_ref)
        # print(self.Delta_sum_ref_90)
        # print(self.Delta_sum_ref_110)
        # 1회 최대 매수목록 / 최근 5일간 체결강도 평균 :: 적용 옵션매수 델타값
        self.Buy_Item_Max_Cnt = Buy_Item_Max_Cnt

    def step_runprice_delta_check(self):
        # 변수선언
        item_list_cnt = {'code_no': [], 'cnt': []}
        Delta_sum = 0
        for p in range(len(self.haga_pass_items['code'])):
            for i in range(len(self.db_option_pickup['monthmall'])):
                if self.haga_pass_items['step_diff'][p] == self.db_option_pickup['step_diff'][i]:
                    if self.haga_pass_items['run_price'][p] == self.db_option_pickup['price_in'][i]:
                        item_cnt = 0
                        Delta_sum_fu = Delta_sum + self.db_option_pickup['Delta'][i]
                        while (Delta_sum < self.Delta_sum_ref_90) and (Delta_sum_fu < self.Delta_sum_ref_110):
                            Delta_sum += self.db_option_pickup['Delta'][i]
                            Delta_sum_fu = Delta_sum + self.db_option_pickup['Delta'][i]
                            item_cnt += 1
                        if item_cnt != 0:
                            # 동일종목은 한 바구니에
                            if len(item_list_cnt['code_no']) == 0:
                                item_list_cnt['code_no'].append(self.haga_pass_items['code'][p])
                                item_list_cnt['cnt'].append(item_cnt)
                            elif self.haga_pass_items['code'][p] in item_list_cnt['code_no']:
                                for c in range(len(item_list_cnt['code_no'])):
                                    if self.haga_pass_items['code'][p] == item_list_cnt['code_no'][c]:
                                        item_list_cnt['cnt'][c] += item_cnt
                            else:
                                item_list_cnt['code_no'].append(self.haga_pass_items['code'][p])
                                item_list_cnt['cnt'].append(item_cnt)
            # print(Delta_sum)

        # 동일옵션 > Buy_Item_Max_Cnt
        same_option_bic = True
        for i in range(len(item_list_cnt['cnt'])):
            if item_list_cnt['cnt'][i] >= self.Buy_Item_Max_Cnt:
                same_option_bic = False

        if (self.Delta_sum_ref_90 < Delta_sum < self.Delta_sum_ref_110) and (same_option_bic == True):
            return item_list_cnt
        else:
            # 다시검색
            # 검색된 종목건수에서 1을 빼서 다시 검색을 시도한다.
            if len(item_list_cnt['cnt']) != 0:
                for i in range(item_list_cnt['cnt'][0], 0, -1):
                    # 다시검색 함수(처음으로 더한 종목코드 건수 보다 하나적게 더해보기)
                    item_list_cnt = self.delta_check_re(i)
                    # 다시검색 함수에서 구한값 리턴
                    if item_list_cnt != None:
                        return item_list_cnt

            # 변수선언
            item_list_cnt = {'code_no': [], 'cnt': []}
            return item_list_cnt

    def delta_check_re(self, first_cnt):
        # 변수선언
        item_list_cnt = {'code_no': [], 'cnt': []}
        Delta_sum = 0
        for p in range(len(self.haga_pass_items['code'])):
            for i in range(len(self.db_option_pickup['monthmall'])):
                if self.haga_pass_items['step_diff'][p] == self.db_option_pickup['step_diff'][i]:
                    if self.haga_pass_items['run_price'][p] == self.db_option_pickup['price_in'][i]:
                        item_cnt = 0
                        Delta_sum_fu = Delta_sum + self.db_option_pickup['Delta'][i]
                        while (Delta_sum < self.Delta_sum_ref_90) and (Delta_sum_fu < self.Delta_sum_ref_110) and (first_cnt > item_cnt):
                            Delta_sum += self.db_option_pickup['Delta'][i]
                            Delta_sum_fu = Delta_sum + self.db_option_pickup['Delta'][i]
                            item_cnt += 1
                        if item_cnt != 0:
                            # 동일종목은 한 바구니에
                            if len(item_list_cnt['code_no']) == 0:
                                item_list_cnt['code_no'].append(self.haga_pass_items['code'][p])
                                item_list_cnt['cnt'].append(item_cnt)
                            elif self.haga_pass_items['code'][p] in item_list_cnt['code_no']:
                                for c in range(len(item_list_cnt['code_no'])):
                                    if self.haga_pass_items['code'][p] == item_list_cnt['code_no'][c]:
                                        item_list_cnt['cnt'][c] += item_cnt
                            else:
                                item_list_cnt['code_no'].append(self.haga_pass_items['code'][p])
                                item_list_cnt['cnt'].append(item_cnt)
            if p == 0:
                first_cnt = 255
            # print(Delta_sum)

        # 동일옵션 > Buy_Item_Max_Cnt
        same_option_bic = True
        for i in range(len(item_list_cnt['cnt'])):
            if item_list_cnt['cnt'][i] >= self.Buy_Item_Max_Cnt:
                same_option_bic = False

        if (self.Delta_sum_ref_90 < Delta_sum < self.Delta_sum_ref_110) and (same_option_bic == True):
            return item_list_cnt

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # delta = Delta
    delta = Delta(haga_pass_items, self.output_put_option_data, Delta_sum_ref)
    put_item_list_cnt = delta.delta_check()
    # print(put_item_list_cnt)