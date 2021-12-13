import argparse
import logging
import os

import requests

from dotenv import load_dotenv
from requests import HTTPError
from terminaltables import AsciiTable


def predict_avg_salary(salary_from, salary_to):
    if salary_from or salary_to:
        if not salary_from:
            expected_salary = salary_to * 0.8
        elif not salary_to:
            expected_salary = salary_from * 1.2
        else:
            expected_salary = (salary_to + salary_from) / 2
        return expected_salary


def predict_rub_salary_hh(vacancy, period):
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
    }
    salaries = []
    page = 0
    url = "https://api.hh.ru/vacancies"
    param = {
        "text": vacancy,
        "period": period,
        "page": page,
    }
    while True:
        response_page = requests.get(url, params=param, headers=headers)
        response_page.raise_for_status()
        logging.warning(response_page.status_code)
        response_vacancy = response_page.json()
        if page == response_vacancy["pages"]-1:
            break
        for vacancy in response_vacancy["items"]:
            if vacancy["salary"] and vacancy["salary"]["currency"] == "RUR":
                expected_salary = predict_avg_salary(vacancy["salary"]["from"], vacancy["salary"]["to"])
                if expected_salary:
                    salaries.append(expected_salary)
        param['page'] += 1
    return response_vacancy["found"], salaries


def predict_rub_salary_sj(vacancy, token, period):
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "X-Api-App-Id": token,
    }
    salaries = []
    page = 0
    url = "https://api.superjob.ru/2.0/vacancies"
    param = {
        "period": period,
        "town": "Москва",
        "keywords": vacancy,
        "currency": "rub",
        "count": 100,
        "page": page,
    }
    while True:
        response_page = requests.get(url, params=param, headers=headers)
        response_page.raise_for_status()
        logging.warning(response_page.status_code)
        collecting_vacancies = response_page.json()
        if collecting_vacancies['more']:
            if page >= collecting_vacancies["total"]:
                break
        if page >= collecting_vacancies["total"]:
            break
        for vacancy in collecting_vacancies["objects"]:
            expected_salary = predict_avg_salary(vacancy["payment_from"], vacancy["payment_to"])
            if expected_salary:
                salaries.append(expected_salary)
        param['page'] += 1
        # sj_collecting_vacancies = collecting_vacancies["total"]
    # return sj_collecting_vacancies, salaries
    print(collecting_vacancies["total"])
    return collecting_vacancies["total"], salaries


def rouping_vacancies_sj(vacancies, token, period):
    grouped_vacancy = {}
    for vacancy in vacancies:
        total_vacansies, salary_group = predict_rub_salary_sj(vacancy, token, period)
        grouped_vacancies = {
            "vacancies_found": total_vacansies,
            "vacancies_processed": len(salary_group),
            "salary_avg": int(sum(salary_group) / len(salary_group)),
        }
        grouped_vacancy[vacancy] = grouped_vacancies
    return grouped_vacancy


def rouping_vacancies_hh(vacancies, period):
    grouped_vacancy = {}

    for vacancy in vacancies:

        total_vacansies, salary_group = predict_rub_salary_hh(vacancy, period)
        grouped_vacancies = {
            "vacancies_found": total_vacansies,
            "vacancies_processed": len(salary_group),
            "salary_avg": int(sum(salary_group) / len(salary_group)),
        }
        grouped_vacancy[vacancy] = grouped_vacancies
    return grouped_vacancy


def get_vacancy_from_user():
    parser = argparse.ArgumentParser(
        description="The Code collects salary figures for vacancies from two sources: HeadHunter, SuperJob."
    )
    vacancies = ["python", "javascript", "golang", "java", "c++", "typescript", "c#"]
    parser.add_argument(
        "-v", "--vacancy", nargs="+", default=vacancies,
        help="Set the vacancies use arguments: '-v or --vacancy'"
    )
    parser.add_argument(
        "-p", "--period", default=30, help="Set the period use arguments: '-p or --period'"
    )
    args = parser.parse_args()
    vacancies = args.vacancy
    args_period = args.period
    return vacancies, args_period


def build_table(statistic_of_vacancies, title):
    table = [
        ["Язык программирования", "Вакансий найдено", "Вакансий обработано", "Средняя зарплата"]
    ]
    for language, statistic in statistic_of_vacancies.items():
        table.append(
            [
                language, statistic['vacancies_found'],
                statistic["vacancies_processed"],
                statistic["salary_avg"],
            ]
        )
    table_instance = AsciiTable(table, title)
    table_instance.justify_columns[3] = "right"
    table_instance.justify_columns[1] = "center"
    table_instance.justify_columns[2] = "center"
    print(table_instance.table)


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
        vacancies_sj = rouping_vacancies_sj(vacancies, token, period)
        build_table(vacancies_sj, "SuperJob")
        vacancies_hh = rouping_vacancies_hh(vacancies, period)
        build_table(vacancies_hh, "HeadHunter")
    except (HTTPError, TypeError, KeyError) as exc:
        logging.warning(exc)


