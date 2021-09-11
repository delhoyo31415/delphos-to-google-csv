#!/usr/bin/env python3

# Create csv files accepted by Google Suite given Delphos csv files
# Copyright (C) 2021 Pablo del Hoyo Abad <pablodelhoyo1314@gmail.com>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import csv
import secrets
import argparse

from typing import Dict, List, Tuple, Set

VOWELS_WITH_ACCENT = "áéíóúÁÉÍÓÚ"
VOWELS_WITHOUT_ACCENT = "aeiouAEIOU"

PATH = "/Curso {}/"
DOMAIN = "@{}"

FIRSTNAME = "First Name [Required]"
LASTNAME = "Last Name [Required]"
EMAIL = "Email Address [Required]"
ORG_UNIT_PATH = "Org Unit Path [Required]"
PASSWORD = "Password [Required]"
CHANGE_PASSWORD = "Change Password at Next Sign-In"

def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="delphos_google_converter",
        description="Convierte csv generado por Delphos al csv que admite Google Suite"
    )

    parser.add_argument("csv_google", metavar="csv-google", help="Nombre del archivo csv de Google Suite")
    parser.add_argument("domain", metavar="dominio", help="Dominio del instituto (ej iesinsti.com)")
    parser.add_argument("year", metavar="año", help="Año del curso académico (ej 2021-2022)")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--profesores", "-p", metavar="profesores", dest="teachers", action="store",
                        help="Nombre archivo de profesores de delphos (csv)")
    group.add_argument("--alumnos", "-a", metavar="alumnos",
                            dest="students", nargs="?", action="store", const="alumnos-delphos",
                            help=("Nombre del directorio donde se guardan los alumnos de Delphos"
                                    " (ej alumnos-delphos)"))

    parser.add_argument("--output", "-o", action="store", metavar="nombre-salida",
                        help=("Nombre del archivo de salida (directorio en el caso de estudiantes y"
                                " csv para profesores)"))

    args = parser.parse_args()

    return args

def random_number_only_password(digits) -> str:
    return "".join([str(secrets.randbelow(10)) for _ in range(digits)])

def remove_accent(letter) -> str:
    if letter in VOWELS_WITH_ACCENT:
        return VOWELS_WITHOUT_ACCENT[VOWELS_WITH_ACCENT.index(letter)]
    return letter

def remove_all_accents(word) -> str:
    return "".join(remove_accent(letter) for letter in word)

class SchoolPerson:

    def __init__(self, firstname: str, lastname: str):
        self.firstname = firstname
        self.lastname = lastname
        self.password = random_number_only_password(8)
        
        self.email: str = "{}" + DOMAIN
        self.org_path_unit = PATH

    def as_csv_dict(self) -> Dict[str, str]:
        return {
            FIRSTNAME: self.firstname,
            LASTNAME: self.lastname,
            EMAIL: self.email,
            PASSWORD: self.password,
            ORG_UNIT_PATH: self.org_path_unit,
            CHANGE_PASSWORD: "TRUE"
        }

    @property
    def fullname(self) -> str:
        return f"{self.firstname} {self.lastname.strip()}"

    def build_email_user(self) -> str:
        raise NotImplementedError("Método implementado en clases descendientes")

    @classmethod
    def from_csv(cls, csv_data: str) -> str:
        raise NotImplementedError("Método implementado en clases descendientes")

    def __str__(self) -> str:
        return f"{self.firstname} {self.lastname} ({self.email})"

    def __repr__(self) -> str:
        return (f"{self.__class__.__name__}(firstname={self.firstname}, "
                f"lastname={self.lastname}, email={self.email})")

class Teacher(SchoolPerson):
    
    def __init__(self, firstname: str, lastname: str):
        super().__init__(firstname, lastname)
        self.email = self.email.format(self.build_email_user())

    def build_email_user(self) -> str:
        first_surname = self.lastname.split()[0]
        return self.firstname[0].lower() + remove_all_accents(first_surname).lower()

    @classmethod
    def from_csv(cls, csv_data: str):
        lastname, firstname = csv_data.split(", ")
        return cls(firstname.strip(), lastname.strip())

def create_teacher_csv(teachers: List[Teacher], csv_filename: str,
                        fieldnames: str, all_names: Set[str]) -> None:
    with open(csv_filename, "w") as csv_file:
        csv_writer = csv.DictWriter(csv_file, fieldnames)
        csv_writer.writeheader()
        for teacher in teachers:
            if teacher.fullname not in all_names:
                print(f"Creando {teacher} en {teacher.org_path_unit}")
                csv_writer.writerow(teacher.as_csv_dict())


def load_teachers(csv_filename: str) -> List[Teacher]:
    with open(csv_filename, encoding="latin_1") as csv_file:
        csv_reader = csv.reader(csv_file)
        # ignore first row
        next(csv_reader)
        return [Teacher.from_csv(data[0]) for data in csv_reader]

def retrieve_google_csv_data(filename: str) -> Tuple[str, Set[str]]:
    with open(filename) as csv_filename:
        csv_reader = csv.reader(csv_filename)
        all_names = set()

        fieldnames = next(csv_reader)

        for row in csv_reader:
            name = f"{row[0].strip()} {row[1].strip()}"
            all_names.add(name)

    return (fieldnames, all_names)


def main():
    global DOMAIN, PATH

    args = get_args()

    # these two global won't change anymore
    DOMAIN = DOMAIN.format(args.domain)
    PATH = PATH.format(args.year)

    fieldnames, all_names = retrieve_google_csv_data(args.csv_google)

    if args.teachers:
        all_teachers = load_teachers(args.teachers)
        create_teacher_csv(all_teachers, args.output or "profes.csv", fieldnames, all_names)
    elif args.students:
        print(args.students)

if __name__ == "__main__":
    main()