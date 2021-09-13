# delphos-to-google-csv

Script que ayuda a pasar los alumnos en Delphos a la plataforma Google Suite.

## Requisitos
Python 3.8 o superior. No puedo asegurar que funcione en versiones inforiores.

## Uso
### General
`./delphos-to-google-csv csv-google dominio año {generar-alumnos, generar-profesores}`

Tanto si se deseas generar un archivo de csv de profesores o de alumnos, la siguiente información debe estar presente
* `google-csv`: archivo csv descargado desde Google Suite que contiene todos los usuarios que se encuentran en la plataforma. Google Suite te dará a elegir entre un archivo csv con las columnas indispensables o con todas las columnas. Debes elegir este último.
* `dominio`: dominio asociado la organización que se tiene dada de alta en Google Suite. Por ejemplo, <span>iesuninstituto.es</span>. Este campo es necesario para generar el correo
* `año`: curso académico. Información necesaria para generar la dirección de la unidad organizativa. Por ejemplo, 2021-2022.

A continuación debes elegir entre el subcomando `generar-alumnos` o `generar-profesores` en función del csv que desees crear.

### Subcomando `generar-profesores`
`generar-profesores [--salida/-s nombre-salida] csv-profesores`
* `csv-profesores`: archivo csv descargado de Delphos que contiene los nombres de los profesores. En la primera columna aparecen el nombre y los apellidos del profesor en la forma `primer-apellido segundo-apellido, nombre`. En la segunda y última columna se encuentra la asignatura que imparte el profesor aunque esta información es ignorada por el script.

* `--salida/-s`: argumento opcional con el que se indica el nombre del archivo de salida. Por defecto es `profes.csv`

Como resultado obtendrás un csv con aquellos profesores que no se encuentren aún en Google Suite en el formato que esta plataforma admite para hacer una subida masiva.

### Subcomando `generar-alumnos`
`generar-alumnos [--directorio/-d alumnos-delphos][--archivo/a unidad-curso | --manual/-m] [--salida/-s nombre-salida]`

* `--directorio/-d`: este argumento es opcional. Directorio donde se guardan todos los archivos csv de los alumnos descargados de Delphos. El nombre por defecto es `alumnos-delphos`.

* `--manual/-m identificador-curso ruta-organización`: esta opción acepta dos argumentos posicionales obligatorios. El primero es el identificador que utiliza delphos para cada clase en el csv. Por ejemplo, a 1º A de la ESO los identifica como 1º A o a 2º de Bachillerato de Ciencias como 2º BC. Sin embargo para evitar problemas con el símbolo 'º' y el espacio he suprimido este último y sustituido 'º' por '-' por lo que en vez de poner 2º BC debes escribir 2-BC. El siguiente argumento es la ruta en la que quieres que estén los alumnos. Por ejemplo "2º Bachillerato Humanidades". Es importante que este argumento esté entre comillas dobles para que incluya los espacios como parte del argumento.

* `--archivo/-a archivo-curso-ruta`: el problema de la opción `--manual/-m` es que debes ejecutar el script tantas veces como clases tengas, modificando los argumentos posicionales según corresponda. Para evitar ese tedio, puedes crear un archivo csv en el que la primera columna corresponda a la ruta en la que quieres que esté los alumnos de una clase y el identificador de la clase en el formato descrito en el párrafo anterior y pasar el nombre de este como argumento a esta opción.

* `--salida/-s`: este es un argumento opcional. Indica el nombre del directorio donde se guardarán los archivos csv generados. Si no existe el directorio, el script lo creará. Por defecto es `alumnos-nuevos`.

Todos los archivos csv correspondientes a los alumno se generarán dentro del directorio `alumnos-nuevos` o, en caso de que esté presente, el que se haya pasado a a `--salida/-s`.

Las opciones `--manual/-m` y `--archivo/-a` son obligatorios pero mutuamente exclusivos.

## Notas adicionales
[POR COMPLETAR]

## Ejemplos de uso
Supón que el archivo csv descargado de Google Suite lo renombro a `todos.csv`

[POR COMPLETAR]

## Licencia
* El script está bajo la licencia [GPLv3+](https://github.com/delhoyo31415/delphos-to-google-csv/blob/master/LICENSE.txt)

* El <span>README</span>.md está bajo la licencia [CC-BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/deed.es)