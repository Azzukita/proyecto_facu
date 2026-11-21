# Bitácora: evolución de la primera etapa

Grupo 02

## 1. Punto de partida

**Datos de trabajo.**

- Mercado Laboral 2024, trimestres T1 a T4, hogares e individuos. Individuos suma 187.625 registros (T1: 46.050, T2: 47.151, T3: 47.564, T4: 46.860) y cada archivo tiene 235 columnas.
- Ciencia y Tecnología: un período (t424), con 16.484 hogares y 45.192 personas.
- Formato de todos los archivos: separador `;` y codificación utf-8.

**Los faltantes no vienen vacíos, vienen como códigos.** `ESTADO` = 0 es entrevista individual no realizada y `ESTADO` = 4 es menor de 10 años (se confirmó con los datos: el 4 aparece exactamente entre los 0 y los 9 años). `CAT_OCUP` = 0 significa que la pregunta no corresponde. Esto condiciona todo el análisis de completitud y de consistencia.

Antes de armar los módulos se practicó el manejo de archivos con `csv` por niveles: lectura completa, lectura por líneas, `DictReader` con delimitador, acumuladores para no guardar los datos, escritura de resultados, recorrido de una carpeta con muchos archivos y comparación con conjuntos. De ahí sale el estilo del proyecto: procesar sin cargar todo en memoria cuando se puede.

**Estructura inicial.** Carpeta `data/` dentro del proyecto con una carpeta por categoría; `src/` con `config.py`, `rutas.py`, `data_loader.py`, `profiling.py` y `metrics.py`; notebooks por categoría; informes en JSON; y una carpeta `files` por fuera de la estructura principal, que contiene los datos utilizados, separados en dos carpetas `cien``cia``_``y``_``te``cnolo``gia` y `m``ercad``o_la``boral``.`

## 2. Lectura de archivos y detección automática

**Versión inicial de `data_loader.py`:** `leer_filas`, `tipo_de_archivo`, `periodo_de_archivo` y `escanear_datos`. El tipo, el año y el trimestre se deducen del nombre del archivo, así que los archivos se dejan tal como se descomprimen.

`escanear_datos` usaba `config.DIR_DATOS`, que no existía, y el módulo no se podía importar. Se agregó la constante en `config.py`.

Se sumaron tres funciones:

- `iterar_filas`: lee una fila por vez, sin guardar el archivo.
- `buscar_archivos`: devuelve los archivos con filtros opcionales por tipo, categoría, años y trimestres.
- `guardar_reporte`: agrega una sección al JSON sin pisar las demás.

Los valores por defecto de lectura (`delimitador`, `encoding`, `directorio`, `ruta`) pasaron de apuntar a las constantes de `config.py` a ser `None`, y la función los resuelve al llamarla. Así cada función lee la configuración vigente en ese momento.

`buscar_archivos` se partió en `escanear_datos` más `filtrar_archivos`. Con eso se puede escanear el disco una sola vez y filtrar la lista varias veces, como hacen los notebooks.

`leer_columnas` (solo el encabezado, para comparar columnas entre períodos) y `trimestres_faltantes` (revisa que cada trimestre tenga hogar e individuo). `guardar_reporte` crea la carpeta si no existe.

`rutas.listar_carpetas_data`, pensada para listar las categorías. Hoy no se usa y busca en `data/` dentro del proyecto.

**Modificación 1: los datos pasan a una carpeta `files/` fuera del proyecto.** `config.DIR_DATOS` se define como la carpeta `files` al lado del proyecto, y los informes van a `output/` (`DIR_SALIDA` y `RUTA_REPORTE`). Cambiar la ubicación de los datos es modificar una línea.

Con los 8 archivos de Mercado Laboral y los 2 de tecnología, la detección reconoce bien tipo, año y trimestre, incluso con los nombres distintos de tecnología (`hog` e `indiv` en lugar de `hogar` e `individual`, y la `t` en minúscula).

## 3. Consistencia entre edad y trabajo

**Criterios.** Se informan cuatro situaciones:

- Edad entre 10 y 14 con estado ocupacional distinto de inactivo: **ERROR**.
- Edad desde 80 con categoría ocupacional activa (`CAT_OCUP` de 1 a 4): **VERIFICAR**.
- Ocupado con edad menor a la legal, por encima del rango de menores: **VERIFICAR** (criterio propio).
- Jubilado o pensionado menor de 30 años: **VERIFICAR** (criterio propio; es VERIFICAR y no ERROR porque puede ser una pensión por fallecimiento de un familiar).

La edad legal para trabajar es 16 años (Ley 26.390), y vive en `config.EDAD_LEGAL_TRABAJO`.

De los 48 errores de menores, 14 tenían `ESTADO` = 0: son no respuestas, no prueba de que el menor trabaje.

La categoría ocupacional activa incluye a algunos desocupados, que conservan la categoría de su trabajo anterior: de los 120 casos de mayores, 115 son ocupados y 5 son desocupados.

La primera versión recorría el archivo una sola vez, con los umbrales como parámetros. Se pidió después evitar una lista fija de reglas y trabajar con funciones y parámetros por nombre, además de un ejecutor genérico para muchos archivos (`analizar_archivos`) y una suma de resultados (`consolidar_criterios`). La versión actual tiene otro diseño: cada regla es un registro (`_regla`) con nombre, etiqueta, columnas, función y, si corresponde, desagregado; las listas `REGLAS_A2` y `REGLAS_A3` las agrupan, y `evaluar_reglas` las aplica.

`ESTADO` = 0 salió de la regla de menores y pasó a ser una regla propia, `entrevista_no_realizada`, con etiqueta CRÍTICO. Con este cambio, la regla de menores da 34 casos en los 4 trimestres (los 48 de antes menos los 14 sin entrevista).

## 4. Completitud de valores

**F****altantes: **Se distingue faltante real (debía responder y no hay dato) de «no corresponde» (la pregunta no aplica); se informan por separado. `NO_CORRESPONDE` tiene prioridad sobre el vacío, porque en algunas columnas el vacío significa que no aplica. Las reglas están por columna en `config.py`:

- Códigos de no respuesta: -9 en `P47T` y `P21`; 0 en `ITF` e `IPCF`; `ESTADO` = 0; 9 en `CAT_OCUP`, `NIVEL_ED`, `CH08` y en las preguntas de tecnología; 12 y 13 en `IDECIFR`.
- `ITF` = 0 se interpreta como «no responde». Evidencia (T1 2024): el 97,6 % de esos hogares tiene `DECIFR` = 12.
- `P47T` = 0 es un dato válido (persona sin ingresos).
- `GDECCFR` está vacía cuando `MAS_500` = N, porque es el decil de aglomerados de 500.000 habitantes o más. Se informa sin ajustar, con una nota, para que sea comparable con otros grupos.

`PP04D_COD` marca «no corresponde» con campo vacío en T1 y T2 de 2024, y con el texto `NA` desde T3. Se aceptan los dos para que los trimestres sean comparables.

**Diseño del cálculo.** Se cuenta una sola vez (`contar_valores`) y el umbral se aplica aparte (`completitud_con_umbral`). Así se puede cambiar el umbral sin volver a leer los datos. Un año se calcula sumando los conteos de sus trimestres (`sumar_conteos`), no promediando porcentajes, porque los trimestres tienen distinta cantidad de filas. Una columna supera el umbral si su porcentaje de faltantes es mayor al umbral. Si varias columnas empatan con el mayor faltante, se informan todas.

**Variables analizadas.** Las pedidas por el enunciado, dos extra por tipo de archivo (`PP04D_COD` y `P47T` en individuos; `REALIZADA` e `IV1` en hogares) y las que agregó el anexo.

**Modificaciones 2, 3 y 4**: se sumaron variables del anexo a las listas, el informe pasó a mostrarse por trimestre y por año, y se agregaron varios umbrales a comparar: `UMBRALES_FALTANTES_PCT = (5, 10, 20)`, con un archivo de salida por umbral (`ARCHIVO_CALIDAD`).

## 5. Consistencia entre variables, etiquetas y roles

** Modificación 5.1 y 5.2:** nivel educativo universitario con menos de 14 años (**ERROR**) y jubilado menor a la edad de jubilación de su sexo, 65 los varones y 60 las mujeres, según la Ley 24.241

**Modificación 5.3, etiquetas nuevas.** Se sumaron CRÍTICO, ADVERTENCIA e INFO, con un criterio escrito para cada una y un orden de gravedad (`ORDEN_ETIQUETAS`). Reglas asociadas: edad inválida (CRÍTICO), edad de 100 años o más (ADVERTENCIA), entrevista no realizada (CRÍTICO) y dos observaciones sobre desocupados con otros ingresos (INFO).

** Modificación 5.4, roles.** `config.ROLES` define qué columnas le interesan a cada rol (docente, investigador y analista); `informe_por_roles` junta, para cada columna, las reglas que la usan y cuentan como inconsistencia. Agregar un rol es agregar una entrada.

## 6. Tendencias por aglomerado

**`tendencias.py`.** Calcula, para cada aglomerado, la tasa de desempleo y la distribución de la población entre ocupados, desocupados e inactivos.

- La población económicamente activa es ocupados más desocupados. La tasa de desempleo es desocupados sobre PEA, por 100. La distribución se calcula sobre ocupados, desocupados e inactivos; quedan afuera `ESTADO` = 0 y `ESTADO` = 4.
- Todo se pondera con `PONDERA` del archivo de individuos. Las personas sin `PONDERA` se descartan y se cuentan aparte.
- Para semestres y años se suman personas, no porcentajes.
- El usuario elige años y aglomerados escribiendo texto: `interpretar_anios` acepta un año, un rango o una lista, y `interpretar_aglomerados` acepta códigos separados por comas.
- Los aglomerados se informan por nombre (config.AGLOMERADOS).

** Modificación 6.** Las tasas se desagregan por sexo (CH04) y por rango etario (RANGOS\_ETARIOS), y el informe se arma por trimestre, por semestre y por año. Cada período indica qué trimestres incluye y si está completo.

## 7. Ciencia y Tecnología

**Notebook.** Verifica que las columnas sean iguales entre archivos de hogares y entre archivos de individuos, valida la integridad entre hogares e individuos con la tupla (`CODUSU`, `NRO_HOGAR`, `AGLOMERADO`) y calcula la penetración tecnológica. Con el período t424: 16.484 hogares, 45.192 individuos y 0 individuos sin hogar.

**Cómo vienen los archivos de tecnología:**

- Se ponderan con `POND_TIC` (no existe `PONDERA`).
- Hogares trae `IH_II_01` (computadoras) e `IH_II_02` (internet). El celular no está en hogares: está en el archivo de individuos como `IP_III_06`; también `IP_III_04` (internet) e `IP_III_05` (computadora).
- Ninguno de los dos archivos trae `REGION` ni `MAS_500`.
- Hay códigos fuera de los documentados (1 sí, 2 no, 9 no sabe o no responde): `IH_II_01` = 3 (1 caso), `IH_II_02` = 4 (2 casos), `IP_III_05` = 3 (1 caso) e `IP_III_06` = 3 (4 casos).

**A corregir:`calcular_tecnologia` da 0 % en todo.** Busca las columnas `CELULAR`, `INTERNET` y `COMPUTADORA`, que no existen en el archivo. Para el celular hay que agrupar a las personas por hogar con la tupla.

El notebook pide los años 2020, 2021 y 2024, pero en los archivos revisados solo se verificó la presencia de t424.

`validar_consistencia` tiene la ruta fija al período t424 y solo comprueba que cada individuo tenga hogar, no al revés.

**Modificación 7.2: `exportar_informe`.** Guarda un JSON controlando si el archivo ya existe: puede preguntar si sobrescribir o agregar la fecha y la hora al nombre. Diferencia con `guardar_reporte`: no mezcla secciones, por lo que si se responde «sí» al sobrescribir se reescribe todo el archivo.


*---------------------------------------------------------------------*

# Bitácora Segunda etapa de PyEPH.AR

Grupo 02

Este documento reúne las decisiones, implementaciones, alternativas y consultas correspondientes a los Bloques A, B, C y D.

---

# Bloque A: Integración del perfilado de datos (roles y alertas)

## 1. Qué se hizo

- `src/panel_calidad.py`: toda la lógica con pandas (la página de Streamlit solo llama a estas funciones).
- `streamlit/pages/02_carga_y_estado.py`: panel con selector de rol, botón para excluir CRÍTICO y dos pestañas:
  - **Faltantes:** métricas, gráfico y tabla por columna.
  - **Inconsistencias:** gráfico de registros afectados por etiqueta y tabla de cantidad por etiqueta.

## 2. Reutilización de la configuración global

Se reutilizaron: `ROLES`, `ORDEN_ETIQUETAS`, `ETIQUETA_CRITICO`, `DIR_SALIDA`.

## 3. Decisiones y alternativas

**Origen de los datos.** `cargar_todos_los_informes` lee todos los `calidad_datos*.json` de la carpeta de salida. Los informes y trimestres que se ofrecen salen de lo que haya en los archivos, sin listas fijas.

**Bloque de cada informe.** Cada JSON mezcla completitud e inconsistencias. Se distinguen por la clave del trimestre: `columnas` (completitud) o `reglas` (inconsistencias). Así un bloque no se confunde con el otro.

**Roles.** Salen de `config.ROLES`, no se detectan desde los archivos. Cada rol filtra las columnas que analiza.


**Estrategia de visualización.** Se usó la Opción 2 (gráficos) como vista principal: barras de completitud por columna y barras de registros afectados por etiqueta. La tabla detallada va en un desplegable.

---

# Bloque B: Mercado Laboral y Género (P3)

## 1. Estructura

Cálculo en `src/mercado_laboral.py`, gráficos en `src/graficos_mercado_laboral.py`, página P3 solo con filtros y llamadas.

Alternativa descartada: lógica dentro de la página (la consigna lo prohibía y no se puede probar sin Streamlit).

## 2. Carga de datos

`pd.read_csv` con `usecols` y `dtype=str`: solo se leen las 6 columnas necesarias, porque cada archivo pesa unos 21 MB.

Los archivos se buscan con `data_loader.buscar_archivos`, sin rutas fijas: agregar un año es copiar sus archivos en `files/`.

## 3. Definiciones

PEA = ocupados + desocupados (ponderados con `PONDERA`).

Tasa de desempleo = desocupados / PEA × 100.

Distribución sobre `ESTADO` 1, 2 y 3; se excluyen 0 y 4 (criterio heredado de la Etapa 1).

## 4. Anual vs. trimestral

Una sola función con el parámetro `agrupar_por`.

El anual promedia los niveles trimestrales, porque cada trimestre ya representa a toda la población (sumar contaría a cada persona 4 veces).

La tasa anual no se promedia: se calcula sobre esos niveles.

Alternativa descartada: promediar las tasas trimestrales (pesa igual a trimestres con distinta PEA).

## 5. Validación

Los resultados con pandas coinciden con `tendencias.py` (Etapa 1, módulo csv) en trimestral, anual y por sexo.

## 6. Género

`CH04`: 1 = varón, 2 = mujer.

Brecha = mujer − varón en puntos porcentuales (tasa de desempleo, % ocupados, % inactivos).

Usamos `groupby` + `unstack` para pasar estados a columnas, `merge` para unir tasa y distribución y `pivot_table` para pasar sexos a columnas.

## 7. Gráfico elegido

Líneas con un panel por aglomerado y color por sexo.

Alternativas: barras agrupadas (no muestran el tiempo) y mapa de calor (el color es menos preciso).

Limitación: muchos aglomerados generan muchos paneles.

Seleccionamos la librería Altair por la utilidad de sus gráficos interactivos.

---

# Bloque C: Hogares y Tecnología

## 1. Qué se hizo

- `src/hogares_tecnologia.py`: toda la lógica con pandas (la página de Streamlit solo llama a estas funciones).
- `streamlit/pages/04_hogares_tecnologia.py`: dos pestañas:
  1. Penetración tecnológica leída de los JSON de la primera etapa.
  2. Calidad tecnológica vs. vivienda, con gráfico, descripción dinámica y descarga CSV.
- Constantes nuevas al final de `src/config.py` (sección "BLOQUE C").

## 2. Reutilización de la configuración global

Se reutilizaron: `COLS_ID_HOGAR`, `COL_POND_TIC`, `COL_TIC_*`, `TIC_SI/NO`, `REGION_DE_AGLOMERADO`, `NOMBRES_REGIONES`, `AGLOMERADOS`, `DIR_SALIDA`, `SEPARADOR`, `ENCODING`, `COL_PONDERA`.

Se agregaron: `TRIMESTRE_CRUCE_TIC`, `COLS_PESO_CRUCE`, `CATEGORIAS_CALIDAD_TEC`, `VARIABLES_VIVIENDA`, `ETIQUETAS_VIVIENDA`, `MIN_MUESTRA_GRUPO`, `PATRON_INFORME_TECNOLOGIA`, entre otras.

## 3. Decisiones y alternativas

**Clave del cruce.** Tupla `(CODUSU, NRO_HOGAR, AGLOMERADO)`, igual que en la primera etapa. Alternativa: solo `CODUSU` (descartada: no identifica al hogar si la vivienda tiene más de un hogar). Antes de unir se normaliza la clave (espacios y ceros a la izquierda), porque un archivo puede traer `02` y otro `2`.

**De dónde sale cada dato.** Computadora e internet: hogares TIC (`IH_II_01`, `IH_II_02`, `POND_TIC`). Vivienda: hogares de Mercado Laboral del **T4** del mismo año (el módulo TIC se releva en el 4.º trimestre).

**Tipo de merge.** `how="left"` desde TIC con `validate="one_to_one"`: el análisis es sobre hogares TIC y la validación avisa si hay claves repetidas.

Alternativa `inner`: descartada porque ocultaría los hogares sin pareja.

**Integridad referencial.** Se informan en la página: hogares sin pareja, solo en vivienda y claves repetidas (se conserva la primera).

**POND_TIC vs PONDERA.** `POND_TIC` expande la muestra del módulo TIC y es el peso por defecto. `PONDERA` es el de la EPH general; queda como opción avanzada para comparar.

**4 categorías de calidad tecnológica.** Computadora e internet / Solo computadora / Solo internet / Sin computadora ni internet. Se cambian editando `CATEGORIAS_CALIDAD_TEC`. El celular no se incluyó (97 % de los hogares: casi no discrimina).

**Hogares sin respuesta válida** (códigos 9, 3, 4, etc.): quedan fuera del análisis y se cuentan.

**Estructura para el gráfico.** `groupby` + `agg` + `unstack` (permite forzar las 4 categorías aun con 0 hogares y calcular muestra y ponderados juntos). `porcentaje_por_vivienda_pivot` hace lo mismo con `pivot_table` y da el mismo resultado; se mantiene para la hoja de ayuda.

**Gráfico.** Barras horizontales apiladas al 100 % por tipo de vivienda: cada barra suma 100 y se comparan composiciones aunque los grupos tengan tamaños muy distintos.

**Valores por defecto.** Año: el último. Región: todas. Variable: tipo de vivienda. Aglomerados de la pestaña 1: los 5 con más hogares ponderados; regiones: todas.


## 5. Problemas encontrados

- Los textos de la etiqueta de región llevan tilde: `"Región".lower()` daba `"región"` y rompía la búsqueda en el informe. Se resolvió con un diccionario.
- Con un solo año disponible (2024) el mínimo de 3 años consecutivos (`MIN_ANIOS_TIC`) no se cumple; el panel funciona con 1 o más años.

---

# Bloque D: Análisis geoespacial (mapas)

Grupo 02 · Segunda etapa de PyEPH.AR

## 1. Qué pide el bloque

El enunciado pide dos mapas: uno que represente el análisis del Bloque B (desempleo) con opción de verlo por período, y otro con los datos del Bloque C (tecnología). Hay que usar la capa que defina los nombres correctos del territorio argentino y el archivo de coordenadas de los aglomerados que provee la cátedra.

## 2. Datos de entrada

**Coordenadas de los aglomerados (`aglomerados_coordenadas.json`).** Tiene 32 aglomerados. La clave de cada uno es su código de dos dígitos (`02`, `03`, …, `93`) y cada entrada trae el nombre y las coordenadas como [latitud, longitud].

**Capa de provincias (`provincias.geojson`).** Tiene 24 elementos: 23 provincias y la Ciudad Autónoma de Buenos Aires, con fuente IGN. Cada uno trae `id`, `nombre`, `nombre_completo`, `categoria`, `centroide`, `iso_id` e `iso_nombre`.

## 3. Unión entre el código de la EPH y las coordenadas

**El problema.** Al leer el JSON de coordenadas con `pd.read_json`, pandas reinterpreta los códigos `02`, `03`, etc. como números (2, 3, …) y se pierde el cero inicial, así que la unión con el código de dos dígitos no coincide.

**La solución**, aplicada en `regiones.py`, restituye el formato de dos dígitos en el índice:

```python
df.index = df.index.astype(str).str.zfill(2)  # evita que pd.read_json reinterprete '02' como 2
```

Con esto el índice vuelve a ser texto de dos dígitos y puede unirse con el código de aglomerado de los resultados.

## 4. Elección de la herramienta de visualización

Se pensó primero en trabajar con GeoJSON para los gráficos, pero resultó más laborioso a la hora de mostrar mapas interactivos en Streamlit.

Finalmente se utilizó pydeck, que se integra con Streamlit (`st.pydeck_chart`) y permite un mapa interactivo con las coordenadas de los aglomerados.

## 5. Organización del código

Cada archivo tiene una responsabilidad, en línea con la regla del enunciado de que la página de Streamlit invoque funciones modulares y no tenga la lógica de cálculo suelta:

- **`regiones.py`**: carga los datos geográficos y resuelve la unión de códigos descripta arriba.
- **`mapa_indicadores.py`**: une los resultados de los bloques B y C con los aglomerados del mapa.
- **`05_mapa.py`**: es la página de Streamlit.

El recorrido es: los notebooks de la primera etapa generan los JSON, `mapa.py` y `mapa_indicadores.py` los combinan con los aglomerados, y la página los muestra.

## 6. Funcionamiento de la página del mapa

La idea fue separar el país por regiones. Al seleccionar una, la página muestra los datos de esa región y los distintos aglomerados que la componen.

Esta idea fue consultada con la cátedra.

## 7. Consultas a la cátedra

* ¿En caso de ser necesario, está bien reescribir o modificar lo que ya realizamos en la primera parte del proyecto (sea para implementar pandas, o para lo que sea necesario), o se debería hacer de otra forma?

*-* Sí, es lo ideal que modifiquen lo que tenían y agreguen sobre el mismo proyecto.

* Para el mapa del Bloque C, ¿se debe mostrar el acceso tecnológico general por aglomerado o el cruce con el tipo de vivienda (por ejemplo, el porcentaje de acceso en casas vs. departamentos)?

*-* Yo mostraría el acceso tecnológico por aglomerado, pero también daría la posibilidad de filtrarlo por tipo de vivienda, así pueden visualizar el cruce que pide el Bloque C.

**Consulta resuelta presencialmente:** En la distribución de carpetas, ¿conviene tener una carpeta específica para Streamlit, con un módulo principal y una carpeta con las páginas?

*-* No recordamos la respuesta específica, pero fue un sí; se ve más ordenado.

## Hoja de ayuda (P6): ejemplos de pandas de los cuatro bloques

### Qué pide la consigna

Explorar, validar con el ayudante y mostrar ejemplos de tres estrategias de
pandas y de cómo se adapta mejor cada una a la solución:

1. Agregaciones simples vs. múltiples: `sum()` y `agg()` con `groupby()`.
2. `merge` con los distintos datasets.
3. Estructura para el gráfico: `pivot_table()` o `groupby()` + `unstack()`.

Además, la página no debe tener lógica de cálculo suelta: debe llamar a
funciones modulares.

### Punto de partida

- `06_ayuda.py` solo explicaba el Bloque A, con texto escrito a mano, y decía
  que ese bloque no usa `agg()`, `merge` ni `pivot_table`.
- `ayuda_bloque_c.py` ya tenía ejemplos con datos reales para el Bloque C,
  pero no estaba conectado a ninguna página.
- Los Bloques B y D no tenían nada en la hoja de ayuda.

### Estructura elegida

- Un módulo por bloque (`ayuda_bloque_a.py`, `_b.py`, `_c.py`, `_d.py`) con
  su lista de ejemplos, un resumen de lo que el bloque usa de verdad, una
  función `preparar_datos` y una función `son_equivalentes`.
- `ayuda_comun.py` con lo que comparten los cuatro: el molde del ejemplo
  (`Ejemplo`), los tres temas de la consigna, `ejecutar`, `codigo_fuente`,
  `agrupar_por_tema` y `tablas_iguales`.
- `06_ayuda.py` solo recorre los ejemplos de cada bloque y los muestra, una
  pestaña por bloque.

**Alternativas descartadas.** (a) Seguir con texto escrito a mano en
`06_ayuda.py` para cada bloque: se desactualiza apenas cambia el código y
pone cálculo y explicación en la página. (b) Un solo archivo de ayuda para
los cuatro bloques: mezcla datos y dependencias de bloques distintos y
dificulta que cada integrante defienda el suyo.

### Decisiones

Cada ejemplo es una función real y la página muestra su código con `inspect.getsource`

*-*El código que se ve es exactamente el que se ejecuta; no hay una copia que pueda quedar desactualizada.

*-*Los resultados se ven al apretar "Ejecutar ejemplos", con `st.cache_data`

*-* Streamlit ejecuta el código de todas las pestañas; sin botón se leerían los archivos al abrir la página. Con la caché, cada bloque se lee una sola vez. El estado se guarda en `session_state` para que los resultados no desaparezcan al apretar otro botón.

*-*En A y D se agregaron ejemplos demostrativos sobre sus propios datos Esos bloques no usan `agg()`, `unstack` ni `pivot_table`; con solo "no se usa" la hoja de ayuda no mostraría esas estrategias. Los ejemplos están marcados como demostrativos y el resumen de cada pestaña aclara qué usa el código real. |

*-*Sin anotaciones de tipo; `collections.namedtuple` en lugar de `NamedTuple` | Regla del grupo. El molde del ejemplo no cambia.

*-*`tablas_iguales` compara `unstack` con `pivot_table`. Permite afirmar con datos, y no solo en el texto, que las dos estrategias dan lo mismo (tolerancia de redondeo).

*-* Un tema = una constante en `ayuda_comun` | Los cuatro bloques se agrupan igual y la página no repite títulos. |

### Qué usa cada bloque y qué ejemplos se agregaron

**Bloque A (panel de calidad).** El código real usa `groupby().mean()`,
conteos con bucles sobre diccionarios y DataFrames armados con `pd.DataFrame`
desde listas de diccionarios (ya salen en formato ancho). Ejemplos:
suma de registros afectados por etiqueta, `agg()` por trimestre,
`merge` de los roles (`config.ROLES`) con los faltantes (con `indicator`,
equivale a `columnas_sin_datos`) y `unstack` vs. `pivot_table` de faltantes
por columna y trimestre.

**Bloque B (mercado laboral).** El código real usa `groupby().sum()` y
`unstack` (`contar_poblacion_por_estado`), `merge` con `how="left"`
(`_indicadores` y `preparar_datos_mapa`) y `pivot_table`
(`calcular_brechas_genero`). No usa `agg()`. Ejemplos: suma de `PONDERA` por
trimestre, `agg()` con muestra, población y peso promedio, dos `merge`
(distribución con tasa, y con una tabla de nombres de aglomerados) y
`unstack` vs. `pivot_table` de la distribución de estados.

**Bloque C (hogares y tecnología).** El código real usa `groupby().agg()` con
`unstack` y un `merge` `how="left"` con `validate="one_to_one"`. Se
conservaron sus seis ejemplos.

**Bloque D (mapas).** El código real usa un solo `merge` con `how="left"`
(`unir_con_aglomerados`), con los códigos normalizados a dos dígitos. Ejemplos:
suma de ocupados por región, `agg()` con mínimo, máximo y tasa ponderada de la
región, el `merge` del mapa, el mismo `merge` sin normalizar y `unstack` vs.
`pivot_table` de la tasa por región y trimestre.

### Respuestas a las preguntas de la consigna

- **¿`sum()` o `agg()`?** `sum()` cuando hay una sola métrica por grupo;
  `agg()` cuando se quieren varias a la vez con nombre propio (muestra,
  población y peso promedio en B y C; mínimo, máximo y sumas en D). En D la
  tasa de la región se calcula con las sumas y no promediando las tasas de
  los aglomerados, para que quede ponderada.
- **¿`pivot_table` o `groupby` + `unstack`?**
  - A: ninguna de las dos; arma la tabla ancha directamente al leer el JSON.
  - B: las dos. `unstack` en `contar_poblacion_por_estado`, porque viene de
    un `groupby` y se necesita `fill_value=0` y `reindex` para que ningún
    estado desaparezca; `pivot_table` en `calcular_brechas_genero`, porque
    hay que pasar el sexo a columnas para varios indicadores a la vez.
  - C: `groupby` + `unstack`, según sus ejemplos 5 y 6.
  - D: ninguna en el módulo; el mapa pinta un período por vez.
  - En los cuatro bloques las dos estrategias dan el mismo resultado
    (la página lo verifica).
- **¿Qué `merge` se usó y con qué datasets?** B: dos tablas derivadas de
  individuos por (año, trimestre, aglomerado). C: hogares TIC con hogares de
  vivienda por (CODUSU, NRO_HOGAR, AGLOMERADO). D: aglomerados con resultados
  por código. El cruce de individuos con hogares es del Bloque C.

### Problemas encontrados

1. `ayuda_bloque_c.py` no estaba conectado a ninguna página y usaba
   anotaciones de tipo (`NamedTuple`, `Callable`). Se reescribió con el molde
   común y sin anotaciones.
2. A y D no usaban `agg()`, `unstack` ni `pivot_table`. Se resolvió con
   ejemplos demostrativos sobre sus propios datos.
3. Los informes del Bloque A no están en el repositorio (los generan los
   notebooks). `preparar_datos` lanza `FileNotFoundError` y la página muestra
   un aviso en lugar de un error.
4. En D, los códigos de aglomerado difieren entre el JSON de coordenadas
   ("02") y los resultados ("2"). El ejemplo 4 lo muestra: sin normalizar, 8
   aglomerados quedan sin pareja.

### Cómo se probó

- Se ejecutaron los 23 ejemplos (5 de A, 6 de B, 6 de C y 6 de D) con los
  datos del repositorio. Todos devuelven tablas con datos y `unstack` y
  `pivot_table` coinciden en los cuatro bloques.
- Se probó la página con la herramienta de pruebas de Streamlit (`AppTest`),
  apretando cada botón y cambiando el año del Bloque C. Sin errores.
- Se probaron los casos sin datos (sin informes y sin archivos de
  individuos): la página muestra un aviso.
- **Límites:** las pruebas usaron los archivos que hay en el repositorio
  (individuos de T1 y T2 de 2024, hogares y TIC de 2024). No se probó en
  navegador. [Completar con la prueba en una máquina del grupo con los datos
  completos.]

### Cómo agregar un ejemplo o un bloque

- **Un ejemplo:** escribir una función en el módulo del bloque y sumar un
  `Ejemplo(tema, titulo, explicacion, funcion, entradas)` a `EJEMPLOS`.
  Aparece sola en la página, en su tema.
- **Un bloque:** crear `ayuda_bloque_x.py` con `EJEMPLOS`, `RESUMEN`,
  `preparar_datos` y `son_equivalentes`, y agregar una pestaña en
  `06_ayuda.py` que llame a `mostrar_ejemplos`.

### Consultas al ayudante

[Completar con la fecha y la respuesta real de cada consulta; no escribir
nada que no haya ocurrido.]

- Qué estrategias de agrupamiento mostrar en los bloques que no usan `agg()` ni
  `pivot_table`, y si alcanzan los ejemplos demostrativos. Respuesta: [ ]
- Si conviene mostrar `unstack` y `pivot_table` como alternativas
  equivalentes o justificar solo la elegida. Respuesta: [ ]

### Responsables

Cada integrante debe poder explicar los cuatro módulos en la defensa.
Responsable de la revisión de cada pestaña: A [ ], B [ ], C [ ], D [ ].