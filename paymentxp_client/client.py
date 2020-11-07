from datetime import date
from typing import Dict, List, Optional

import requests
from requests import Response


class BillingAddress:
    address: str
    city: str
    state: str
    zipcode: str

    def __init__(
            self,
            address: str,
            city: str,
            state: str,
            zipcode: str):
        self.address = address
        self.city = city
        self.state = state
        self.zipcode = zipcode

    def __eq__(self, other) -> bool:
        return (
            self.address == other.address and
            self.city == other.city and
            self.state == other.state and
            self.zipcode == other.zipcode
        )


class CardInfo:
    name: str
    number: str
    expiration: str
    cvv2: str
    address: BillingAddress

    def __init__(
            self,
            name: str,
            number: str,
            expiration: str,
            cvv2: str,
            address: BillingAddress):
        self.name = name
        self.number = number
        self.expiration = expiration
        self.cvv2 = cvv2
        self.address = address

    def __eq__(self, other) -> bool:
        return (
            self.name == other.name and
            self.number == other.number and
            self.expiration == other.expiration and
            self.cvv2 == other.cvv2 and
            self.address == other.address
        )


class PaymentXpClient:
    BASE_URL: str = 'https://webservice.paymentxp.com/wh'
    DATE_FORMAT: str = '%m%d%Y'

    merchant_id: str
    merchant_key: str

    def __init__(self, merchant_id: str, merchant_key: str):
        self.merchant_id = merchant_id
        self.merchant_key = merchant_key

    def charge_card(self, card_info: CardInfo, amount: float) -> Dict[str, str]:
        return self._make_request(
            'webhost.aspx',
            {
                'CardNumber': card_info.number,
                'ExpirationDateMMYY': card_info.expiration,
                'BillingFullName': card_info.name,
                'BillingAddress': card_info.address.address,
                'BillingZipCode': card_info.address.zipcode,
                'BillingCity': card_info.address.city,
                'BillingState': card_info.address.state,
                'MerchantID': self.merchant_id,
                'MerchantKey': self.merchant_key,
                'TransactionAmount': amount,
                'TransactionType': 'CreditCardCharge'
            }
        )

    def cancel_recurring_charge(self, recur_id: str) -> Dict[str, str]:
        data = {
            'MerchantID': self.merchant_id,
            'MerchantKey': self.merchant_key,
            'RecurID': recur_id,
            'TransactionType': 'CreditCardRecurringUpdate',
            'IsEnabled': 0
        }
        return self._make_request(
            'webHost.aspx',
            data
        )

    def create_recurring_charge(
            self,
            card_info: CardInfo,
            amount: float,
            start_date: date,
            end_date: date) -> Dict[str, str]:
        day_of_month = start_date.day
        # In order to have consistent monthly billing,
        # if this supposed to start on a day past the 28th
        # which not all months will have, we'll just start
        # on the 1st day of the next month instead
        if day_of_month > 28:
            if start_date.month == 12:
                new_month = 1
                new_year = start_date.year + 1
            else:
                new_month = start_date.month + 1
                new_year = start_date.year
            start_date = date(new_year, new_month, 1)
            day_of_month = 1

        response = self._make_request(
            'webhost.aspx',
            {
                'CardNumber': card_info.number,
                'ExpirationDateMMYY': card_info.expiration,
                'BillingFullName': card_info.name,
                'BillingAddress': card_info.address.address,
                'BillingZipCode': card_info.address.zipcode,
                'BillingCity': card_info.address.city,
                'BillingState': card_info.address.state,
                'MerchantID': self.merchant_id,
                'MerchantKey': self.merchant_key,
                'TransactionAmount': amount,
                'OccurenceOption': 2,  # 2 means monthly (1 is daily)
                # MonthlyOption 1 means we'll set the explicit day of month,
                'MonthlyOption': 1,
                'MonthOfYearOption': 1,  # Which months it applies. 0 means all
                'DayOfMonthOption': day_of_month,
                'StartDate': start_date.strftime(self.DATE_FORMAT),
                'EndDate': end_date.strftime(self.DATE_FORMAT),
                'TransactionType': 'CreditCardRecurringCharge'
            }
        )
        return response

    def get_paysafe_token(self, card_info: CardInfo) -> str:
        response = self._make_request(
            'GetToken.aspx',
            {
                'CardNumber': card_info.number,
                'CVV2': card_info.cvv2,
                'ExpirationDateMMYY': card_info.expiration,
                'MerchantID': self.merchant_id
            }
        )
        return response['Token']

    def update_recurring_charge(
            self,
            recur_id: str,
            card_info: Optional[CardInfo] = None,
            amount: Optional[float] = None,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None,
            interval: Optional[int] = None) -> Dict[str, str]:
        data = {
            'MerchantID': self.merchant_id,
            'MerchantKey': self.merchant_key,
            'RecurID': recur_id,
            'TransactionType': 'CreditCardRecurringUpdate'
        }
        if card_info is not None:
            data.update({
                'CardNumber': card_info.number,
                'ExpirationDateMMYY': card_info.expiration,
                'BillingFullName': card_info.name,
                'BillingAddress': card_info.address.address,
                'BillingZipCode': card_info.address.zipcode,
                'BillingCity': card_info.address.city,
                'BillingState': card_info.address.state,
            })
        if amount is not None:
            data['TransactionAmount'] = amount
        if start_date is not None:
            data['StartDate'] = start_date.strftime(self.DATE_FORMAT)
        if end_date is not None:
            data['EndDate'] = end_date.strftime(self.DATE_FORMAT)

        return self._make_request(
            'webHost.aspx',
            data
        )

    def _get_url(self, path: str) -> str:
        return "{0}/{1}".format(self.BASE_URL, path)

    def _make_request(self, path: str, data: Dict[str, any]) -> Dict[str, str]:
        request_url = self._get_url(path)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        response = requests.post(request_url, data, headers=headers)
        if response.status_code != 200:
            raise Exception("Request failed: {0} {1}".format(
                response.status_code, response.content))
        return self._parse_response(response)

    @staticmethod
    def _parse_response(response: Response) -> Dict[str, str]:
        pieces: List[str] = response.content.decode('utf-8').split('&')
        output = {}
        for piece in pieces:
            split_piece = piece.split('=')
            if len(split_piece) == 2:
                key = split_piece[0]
                value = split_piece[1]
            elif len(split_piece) == 1:
                key = split_piece[0]
                value = ''
            else:
                continue
            output[key] = value
        return output
