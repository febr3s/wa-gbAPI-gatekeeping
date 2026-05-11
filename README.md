Instrucciones de uso:

1. Configuración de Python y environment variable
	{PASOS PENDIENTES DE ESCRIBIR}
{orientar al usuario respecto al punto en que se encuentra}
2. Ejecuta ´wikidata.py´. Para cambiar de país debes editar:
	- el segundo parámetro de la línea 2 (´wd: Q717´)
	- la línea   ´FILTER(?date_of_death < "1965-01-01"^^xsd:dateTime)´, donde la fecha de muerte debe adaptarse a la que es legal en cada país
	- las líneas que dicen ´venezuelan_authors.json´
{orientar al usuario respecto al punto en que se encuentra}
3. Ejecuta ´gbooks_json_all-authors.py´. Si cambiaste de país, antes debes:
	- cambiar el nombre del INPUT_JSON_FILE al que definiste en el paso anterior
{orientar al usuario respecto al punto en que se encuentra: todos los autores muertos antes de la fecha indicada tendrán un mini dataset con una lista de todos sus libros en Google Books}

4. Ejecuta ´parser.py´
{orientar al usuario respecto al punto en que se encuentra: el script revisará todos los mini datasets y copiará en dos csv solo los que tienen pdf: en un csv los que aparentemente encajan con el criterio, y en otro los que aparentemente no encajan. El criterio: que realmente sean autores de la nacionalidad correspondiente}

5. Abre el archivo ´consolidated_matches.csv´ y revisa los resultados para borrar los que no correspondan. A veces Wikidata da "falsos positivos". Es conveniente tomar nota de estos antes de eliminarlos para corregir el dato de nacionalidad en la base de datos más adelante.

6. Abre el archivo ´consolidated_non_matches.csv´ y revisa los resultados. A veces los metadatos de Google Books mal administrados dan "falsos negativos". Borra todos los non-matches confirmados y conserva los que resultaron sí ser matches.

7. Fusiona ambos csv en un archivo llamado ´consolidated_all_pdf_matches.csv´. Puedes hacerlo vía línea de comandos o en un editor de texto.

{orientar al usuario respecto al punto en que se encuentra: tienes en un csv un dataset con todos los libros de dominio público del país definido con descarga disponible en Google Books}

8. Ejecuta ´parser_to_zotero.py

{orientar al usuario respecto al punto en que se encuentra: tienes esos datos listos para importarlos a Zotero y crear una base de datos accesible, descargable y compatible con un generador de sitios web MOREL}

9. Importa a Zotero

10. Genera tu sitio web