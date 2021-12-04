import argparse
import logging
import os
from pprint import pprint

import requests
from requests import HTTPError
from dotenv import load_dotenv
from itertools import count
from terminaltables import AsciiTable


def predict_salary_avg(salary_from, salary_to):
    if not salary_from:
        expected_salary = salary_to * 0.8
    elif not salary_to:
        expected_salary = salary_from * 1.2
    else:
        expected_salary = (salary_to + salary_from) / 2
    return expected_salary


def predict_rub_salary_hh(vacancies, period):
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
    }
    city = 1
    for vacancy in vacancies:
        salary_group = []
        for page in count():
            url = "https://api.hh.ru/vacancies"
            param = {
                "text": f"{vacancy}",
                "area": city,
                "period": period,
                "only_with_salary": "true",
                "page": page,
            }
            response = requests.get(url, params=param, headers=headers)
            response.raise_for_status()
            logging.warning(response.status_code)
            data = response.json()
            if page+1 == data["pages"]+1:
                break
            # print(page, data["pages"])
            for salary in data["items"]:
                if salary["salary"]["currency"] == "RUR":
                    if salary["salary"]["from"] or salary["salary"]["to"]:
                        salary_avg = predict_salary_avg(salary["salary"]["from"], salary["salary"]["to"])
                        salary_group.append(salary_avg)

        return data["found"], salary_group, salary["area"]["name"]


def predict_rub_salary_sj(vacancies, token, period):
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "X-Api-App-Id": token,
    }
    for vacancy in vacancies:
        salary_group = []
        for page in count():
            url = "https://api.superjob.ru/2.0/vacancies"
            param = {
                "period": period,
                "town": "Москва",
                "keywords": f"{vacancy}",
                "payment_no_agreement": 1,
                "currency": "rub",
                "count": 20,
            }
            response = requests.get(url, params=param, headers=headers)
            response.raise_for_status()
            logging.warning(response.status_code)
            data = response.json()
            if page == data["total"]+1:
                break
            print(page, data["total"])
            for salary in data["objects"]:
                if salary["payment_from"] or salary["payment_to"]:
                    salary_avg = predict_salary_avg(salary["payment_from"], salary["payment_to"])
                    salary_group.append(salary_avg)
        pprint(salary_group)
        return data["total"], salary_group, salary["town"]["title"]


def grouped_vacancies_hh(vacancies, period):
    grouped_vacancies = {}
    for vacancy in vacancies:
        vacancies_found, salary_group, city = predict_rub_salary_hh(vacancy, period)
        salary_avg = int(sum(salary_group)) / len(salary_group)
        grouped_vacancies[f"{vacancy}"] = {
            "vacancies_found": vacancies_found,
            "vacancies_processed": len(salary_group),
            "sum_salary": int(salary_avg),
            "city": city
        }
    return grouped_vacancies


def grouped_vacancies_sj(vacancies, token, period):
    grouped_vacancies = {}
    for vacancy in vacancies:
        vacancies_found, salary_group, city = predict_rub_salary_sj(vacancy, token, period)
        salary_avg = int(sum(salary_group)) / len(salary_group)
        grouped_vacancies[f"{vacancy}"] = {
            "vacancies_found": vacancies_found,
            "vacancies_processed": len(salary_group),
            "sum_salary": int(salary_avg),
            "city": city
        }
    return grouped_vacancies


def statistic_for_table_hh(vacancies, period):
    vacancies_hh = grouped_vacancies_hh(vacancies, period)
    for final_data_language in vacancies:
        title_hh = f"HeadHunter - {vacancies_hh[final_data_language]['city']}"
        hh_table_data = [
            ["Язык программирования", "Вакансий найдено", "Вакансий обработано", "Средняя зарплата"]
        ]
        for final_data_language in vacancies:
            hh_table_data.append(
                [
                    final_data_language, vacancies_hh[final_data_language]["vacancies_found"],
                    vacancies_hh[final_data_language]["vacancies_processed"],
                    vacancies_hh[final_data_language]["sum_salary"],
                ]
            )
    return hh_table_data, title_hh


def statistic_for_table_sj(vacancies, token, period):
    vacancies_sj = grouped_vacancies_sj(vacancies, token, period)
    for final_data_language in vacancies:
        title_sj = f"SuperJob - {vacancies_sj[final_data_language]['city']}"
        sj_table_data = [
            ["Язык программирования", "Вакансий найдено", "Вакансий обработано", "Средняя зарплата"]
        ]
        for final_data_language in vacancies:
            sj_table_data.append(
                [
                    final_data_language, vacancies_sj[final_data_language]["vacancies_found"],
                    vacancies_sj[final_data_language]["vacancies_processed"],
                    vacancies_sj[final_data_language]["sum_salary"],
                ]
            )
    return sj_table_data, title_sj


def get_vacancy_from_user():
    parser = argparse.ArgumentParser(
        description="The Code collects salary figures for vacancies from two sources: HeadHunter, SuperJob."
    )
    vacancies = ["golang", "javascript", "typescript"]
    parser.add_argument(
        "-v", "--vacancy", nargs="+", default=vacancies, help="Set the vacancies use arguments: '-v or --vacancy'"
    )
    parser.add_argument(
        "-p", "--period", nargs="+", default=30, help="Set the period use arguments: '-p or --period'"
    )
    args = parser.parse_args()
    args_vacancy = args.vacancy
    args_period = args.period
    return args_vacancy, args_period


def build_table(hh_table_data, title_hh):
    table_instance = AsciiTable(hh_table_data, title_hh)
    table_instance.justify_columns[3] = "right"
    table_instance.justify_columns[1] = "center"
    table_instance.justify_columns[2] = "center"
    return table_instance.table


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.WARNING,
        filename="logs.log",
        filemode="w",
        format="%(asctime)s - [%(levelname)s] - %(funcName)s() - [line %(lineno)d] - %(message)s",
    )
    load_dotenv()
    token = os.getenv("API_KEY_SUPERJOB")
    vacancies, period = get_vacancy_from_user()
    try:
        # hh_table_data, title_hh = statistic_for_table_hh(vacancies, period)
        # print(build_table(hh_table_data, title_hh))


        # table_instance = AsciiTable(hh_table_data, title_hh)
        # table_instance.justify_columns[3] = "right"
        # table_instance.justify_columns[1] = "center"
        # table_instance.justify_columns[2] = "center"
        # print("\n", table_instance.table)

        sj_table_data, title_sj = statistic_for_table_sj(vacancies, token, period)
        print(build_table(sj_table_data, title_sj))
        # table_instance = AsciiTable(sj_table_data, title_sj)
        # table_instance.justify_columns[3] = "right"
        # table_instance.justify_columns[1] = "center"
        # table_instance.justify_columns[2] = "center"
        # print("\n", table_instance.table)
    except (HTTPError, TypeError, KeyError) as exc:
        logging.warning(exc)
        raise exc



