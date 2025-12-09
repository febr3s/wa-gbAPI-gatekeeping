# Integración básica Wikidata y Google books (approach 1, solo buscando las obras listadas en Wikidata)

Script 1. Genera un csv en _data con datos de Wikidata

Nombres (separados por ;), Viaf, obras (separadas por ;) {{quizá otros datos para generar las páginas de autor}}

Script 2.

Usa el csv para pedirle a GB que por cada row:

i) dame una lista de obras disponibles en el dominio público atribuidas a nombre(1), nombre(2), etc
ii) chequea qué obras no están ya en la base de datos Zotero
iii) agrega estas obras a un csv con formato Zotero

Jekyll:

Combina las dos colecciones tipo Zotero en las listas


# Integración básica Wikidata y Google books (approach 2, buscando todas las obras de los autores definidos que están disponibles en el dominio público)

## Overview

Script 1. Genera un csv en _data con datos de Wikidata

Nombres (separados por ;), Viaf, {{quizá otros datos para generar las páginas de autor}}

Script 2.

Usa el csv para pedirle a GB que por cada row:

i) dame una lista de obras disponibles en el dominio público atribuidas a nombre(1), nombre(2), etc
ii) chequea qué obras no están ya en la base de datos Zotero
iii) agrega estas obras a un csv con formato Zotero

El formato de request en GBapi es, más o menos 

https://www.googleapis.com/books/v1/volumes?q=inauthor:%20Shakespeare&filter=full



## Jekyll:

Combina las dos colecciones tipo Zotero en las listas

`{% if site.data.file1 and site.data.file2 %} <!-- Your loop here --> {% endif %}`

`{% assign combined = site.data.file1 | concat: site.data.file2 | sort: "date" %}`

`{% assign combined = site.data.file1 | concat: site.data.file2 %}{% for item in combined limit: 10 %}{{ item.title }}{% endfor %}`


## pasos para ejecutar

### URL para acceder con gbapi a descargables en dominio público

`https://www.googleapis.com/books/v1/volumes?q=inauthor:%22{{Name+Separated+by+Plus}}%22`

### bugs de Google Books API y solución para obtener los resultados completos de un autor

Algunas inconsistencias:

- Google API Forums envía a página de Contenido no disponible
- No funciona combinar el filtro full con el filtro inauthor
- En la búsqueda de web la búsqueda "inauthor:"Domingo+Faustino+Sarmiento"" muestra 74 resultados, pero la API:
 - No muestra el total de items de la búsqueda sino un número que parece arbitrario, 1000000
 - A pesar de que le pido 40 resultados, solo muestra 20, y no hay forma de saber cuántos resultados hay en realidad
 - Usando el filtro startIndex de 20 en 20 se va revelando la lista, pero cuando hago el startIndex en 60, no muestra los resultados. Y esta vez sí dice el número correcto de totalItems (probablemente indicando que no me los puede mostrar porque la cantidad de resultados pedidos supera la cantidad de resultados disponibles)
- En realidad, incluso si no pides un número específico de resultados, el último lote falla porque el default, que son 10, supera los resultados disponibles
- Tuve que bajar el startIndex a 65 para que me los mostrara
- Como está escrito en el cuaderno, hay que ir de 20 en veinte, y cuando no muestra items tomar el número de total items, y repetir el query aplicando el filtro maxResults


### hacer un get request para obtener una lista de autores de determinado país fallecidos antes de determinada fecha

```
SELECT DISTINCT ?author ?authorLabel ?date_of_death WHERE {
  ?author wdt:P31 wd:Q5;               # Instance of human
          wdt:P27 wd:Q717;              # Country of citizenship (Vwnwzuela)
          wdt:P570 ?date_of_death.     # Date of death
  FILTER(?date_of_death < "1965-01-01"^^xsd:dateTime)
  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
}
ORDER BY ?date_of_death
```

### variación con obras publicadas

```
SELECT DISTINCT ?author ?authorLabel ?date_of_death ?work ?workLabel
WHERE {
  # Block 1: Base author list
  ?author wdt:P31 wd:Q5;
          wdt:P27 wd:Q717;
          wdt:P570 ?date_of_death.
  FILTER(?date_of_death < "1965-01-01"^^xsd:dateTime)
  
  # Block 2: Optional link to works
  OPTIONAL {
    ?work wdt:P50 ?author.
  }
  
  # Single label service for both authors and works
  SERVICE wikibase:label {
    bd:serviceParam wikibase:language "es,en,fr".   # Spanish first, English and French fallback
  }
}
ORDER BY ?date_of_death ?authorLabel
```

#### Formula to identify elegible authors

```
from datetime import datetime

# Get the current date and time
current_datetime = datetime.now()

# Extract the year from the datetime object
current_year = current_datetime.year

# Print the current year
elegible_dead_year = current_year -60
```

#### URL para probar los Wikidata queries

https://query.wikidata.org/

#### URL dinámica para los records que tienen opción de "compra gratis" pero que dicen pdf = false

https://books.google.com/books/download/[TITLE].pdf?id=[VOLUME_ID]&output=pdf

#### Librería Python oficial de Google discovery API's

https://github.com/googleapis/google-api-python-client

# README.md notes

## Setup
1. Get API key from Bitwarden
2. Store in password manager
3. Create `.env` file: `API_KEY=your_key_here`

