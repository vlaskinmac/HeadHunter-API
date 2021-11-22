import logging
import os

import requests
from requests import HTTPError
from dotenv import load_dotenv
from itertools import count
from terminaltables import AsciiTable


def predict_rub_salary_hh(vacancies):
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
    }
    vacancy_grouped = []
    for vacancy in vacancies:
        grouped_vacancies = {}
        collect_salary_avg = []
        for page in count():
            url = "https://api.hh.ru/vacancies"
            param = {
                "text": f"{vacancy}",
                "area": 1,
                "period": 7,
                "only_with_salary": "true",
                "page": page,
            }
            response = requests.get(url, params=param, headers=headers)
            response.raise_for_status()
            logging.warning(response.status_code)
            data = response.json()
            if page == data["pages"]:
                break
            for salary in data["items"]:
                if salary["salary"]["currency"] == "RUR":
                    if not salary["salary"]["from"]:
                        expected_salary = salary["salary"]["to"] * 0.8
                    elif not salary["salary"]["to"]:
                        expected_salary = salary["salary"]["from"] * 1.2
                    else:
                        expected_salary = (salary["salary"]["to"] + salary["salary"]["from"]) / 2
                    collect_salary_avg.append(int(expected_salary))
        grouped_vacancies[f"{vacancy}"] = {
            "vacancies_found": data["found"],
            "vacancies_processed": len(collect_salary_avg),
            "sum_salary": int(sum(collect_salary_avg)),
            "language": vacancy,
            "city": salary["area"]["name"]
        }
        vacancy_grouped.append(grouped_vacancies)
    return vacancy_grouped


def predict_rub_salary_sj(vacancies, token):
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "X-Api-App-Id": f"{token}"
    }
    vacancy_grouped = []
    for vacancy in vacancies:
        grouped_vacancies = {}
        collect_salary_avg = []
        for page in count():
            url = "https://api.superjob.ru/2.0/vacancies"
            param = {
                "period": 7,
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
            if data["total"] // 20 == 0:
                pages = 1
            else:
                pages = data["total"] // 20
            if page == pages:
                break
            for salary in data["objects"]:
                if not salary["payment_from"]:
                    expected_salary = salary["payment_to"] * 0.8
                elif not salary["payment_to"]:
                    expected_salary = salary["payment_from"] * 1.2
                else:
                    expected_salary = (salary["payment_to"] + salary["payment_from"]) / 2
                if int(expected_salary) != 0:
                    collect_salary_avg.append(int(expected_salary))
            grouped_vacancies[f"{vacancy}"] = {
                "vacancies_found": data["total"],
                "vacancies_processed": len(collect_salary_avg),
                "sum_salary": int(sum(collect_salary_avg)),
                "language": vacancy,
                "city": salary["town"]["title"]
            }
        vacancy_grouped.append(grouped_vacancies)
    return vacancy_grouped


def predict_salary(vacancies):
    hh = predict_rub_salary_hh(vacancies)
    sj = predict_rub_salary_sj(vacancies, token)
    grouped_vacancies = {}
    for vacancy_hh in hh:
        for vacancy_sj in sj:
            for key_hh, value_hh in vacancy_hh.items():
                for key_sj, value_sj in vacancy_sj.items():
                    if key_hh == key_sj:
                        vacancies_processed_combined_total = value_sj["vacancies_processed"] + value_hh[
                            "vacancies_processed"]
                        vacancies_found_combined = value_sj["vacancies_found"] + value_hh["vacancies_found"]
                        sum_salary_combined = value_sj["sum_salary"] + value_hh["sum_salary"]
                        avg_combined = sum_salary_combined / vacancies_processed_combined_total
                        hh_avg = value_hh["sum_salary"] / value_hh["vacancies_found"]
                        sj_avg = value_sj["sum_salary"] / value_sj["vacancies_found"]

                        grouped_vacancies[key_hh] = {
                            "vacancies_found": vacancies_found_combined,
                            "vacancies_processed": vacancies_processed_combined_total,
                            "language": value_sj["language"],
                            "avg": int(avg_combined),
                            "city": value_sj["city"],
                            "hh_vacancies_found": value_hh["vacancies_found"],
                            "hh_vacancies_processed": value_hh["vacancies_processed"],
                            "hh_avg": int(hh_avg),
                            "sj_vacancies_found": value_sj["vacancies_found"],
                            "sj_vacancies_processed": value_sj["vacancies_processed"],
                            "sj_avg": int(sj_avg),
                        }
    return grouped_vacancies


def print_table(vacancies):
    data = predict_salary(vacancies)

    title = f"HeadHunter - {data['python']['city']}"
    hh_table_data = [
        ["Язык программирования", "Вакансий найдено", "Вакансий обработано", "Средняя зарплата"]
    ]

    for final_data in data.values():
        hh_table_data.append(
            [
                final_data["language"], final_data["hh_vacancies_found"], final_data["hh_vacancies_processed"],
                final_data["hh_avg"],
            ]
        )

    table_instance = AsciiTable(hh_table_data, title)
    table_instance.justify_columns[3] = "right"
    table_instance.justify_columns[1] = "center"
    table_instance.justify_columns[2] = "center"
    print("\n", table_instance.table)

    title = f"SuperJob - {data['python']['city']}"
    sj_table_data = [
        ["Язык программирования", "Вакансий найдено", "Вакансий обработано", "Средняя зарплата"]
    ]
    for final_data in data.values():
        sj_table_data.append(
            [
                final_data["language"], final_data["sj_vacancies_found"], final_data["sj_vacancies_processed"],
                final_data["sj_avg"],
            ]
        )

    table_instance = AsciiTable(sj_table_data, title)
    table_instance.justify_columns[3] = "right"
    table_instance.justify_columns[1] = "center"
    table_instance.justify_columns[2] = "center"
    print("\n", table_instance.table)

    title = f"Combined table: SuperJob and HeadHunter - {data['python']['city']}"
    combined_table_data = [
        ["Язык программирования", "Вакансий найдено", "Вакансий обработано", "Средняя зарплата"]
    ]
    for final_data in data.values():
        combined_table_data.append(
            [
                final_data["language"], final_data["vacancies_found"], final_data["vacancies_processed"],
                final_data["avg"],
            ]
        )

    table_instance = AsciiTable(combined_table_data, title)
    table_instance.justify_columns[3] = "right"
    table_instance.justify_columns[1] = "center"
    table_instance.justify_columns[2] = "center"
    print("\n", table_instance.table)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.WARNING,
        filename="logs.log",
        filemode="w",
        format="%(asctime)s - [%(levelname)s] - %(funcName)s() - [line %(lineno)d] - %(message)s",
    )
    load_dotenv()
    token = os.getenv("API_KEY_SUPERJOB")
    vacancies = ["python", "javascript", "golang", "java", "c++", "typescript", "c#"]
    try:
        print_table(vacancies)
    except (HTTPError, TypeError, KeyError) as exc:
        logging.warning(exc)
        raise exc
