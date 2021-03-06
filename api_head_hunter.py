import argparse
import logging
import os

import requests

from dotenv import load_dotenv
from itertools import count
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
    url = "https://api.hh.ru/vacancies"
    params = {
        "text": vacancy,
        "period": period,
    }
    for page in count():
        params["page"] = page
        response_of_the_page = requests.get(url, params=params, headers=headers)
        response_of_the_page.raise_for_status()
        logging.warning(response_of_the_page.status_code)
        response_vacancies = response_of_the_page.json()

        for vacancy in response_vacancies["items"]:
            if vacancy["salary"] and vacancy["salary"]["currency"] == "RUR":
                expected_salary = predict_avg_salary(vacancy["salary"]["from"], vacancy["salary"]["to"])
                if expected_salary:
                    salaries.append(expected_salary)
        if page == response_vacancies["pages"]-1:
            break
    return response_vacancies["found"], salaries


def predict_rub_salary_sj(vacancy, token, period):
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "X-Api-App-Id": token,
    }
    salaries = []
    url = "https://api.superjob.ru/2.0/vacancies"
    params = {
        "period": period,
        "town": "Москва",
        "keywords": vacancy,
        "currency": "rub",
        "count": 100,
    }
    for page in count():
        params["page"] = page
        response_of_the_page = requests.get(url, params=params, headers=headers)
        response_of_the_page.raise_for_status()
        logging.warning(response_of_the_page.status_code)
        response_vacancies = response_of_the_page.json()
        for vacancy in response_vacancies["objects"]:
            expected_salary = predict_avg_salary(vacancy["payment_from"], vacancy["payment_to"])
            if expected_salary:
                salaries.append(expected_salary)
        if not response_vacancies["more"]:
            break
    return response_vacancies["total"], salaries


def collect_statistics_sj(vacancies, token, period):
    grouped_vacancies = {}
    for vacancy in vacancies:
        total_vacancies, salaries = predict_rub_salary_sj(vacancy, token, period)
        if salaries:
            avg_salary = int(sum(salaries) / len(salaries))
            vacancy_statistic = {
                "vacancies_found": total_vacancies,
                "vacancies_processed": len(salaries),
                "avg_salary": avg_salary,
            }
            grouped_vacancies[vacancy] = vacancy_statistic
    return grouped_vacancies


def collect_statistics_hh(vacancies, period):
    grouped_vacancies = {}
    for vacancy in vacancies:
        total_vacancies, salaries = predict_rub_salary_hh(vacancy, period)
        if salaries:
            vacancy_statistic = {
                "vacancies_found": total_vacancies,
                "vacancies_processed": len(salaries),
                "avg_salary": int(sum(salaries) / len(salaries)),
            }
            grouped_vacancies[vacancy] = vacancy_statistic
    return grouped_vacancies


def get_vacancy_from_user():
    parser = argparse.ArgumentParser(
        description="The Code collects salary figures for vacancies from two sources: HeadHunter, SuperJob."
    )
    vacancies = ["python", "javascript", "golang", "java", "c++", "typescript", "c#"]

    parser.add_argument(
        "-v", "--vacancy", nargs="+", default=vacancies,
        help="Set the vacancies use arguments: -v or --vacancy"
    )
    parser.add_argument(
        "-p", "--period", default=30, help="Set the period use arguments: -p or --period"
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
                language, statistic["vacancies_found"],
                statistic["vacancies_processed"],
                statistic["avg_salary"],
            ]
        )
    table_instance = AsciiTable(table, title)
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
        vacancies_sj = collect_statistics_sj(vacancies, token, period)
        print(build_table(vacancies_sj, "SuperJob"))
        vacancies_hh = collect_statistics_hh(vacancies, period)
        print(build_table(vacancies_hh, "HeadHunter"))
    except (HTTPError, TypeError, KeyError) as exc:
        logging.warning(exc)


