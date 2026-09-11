/**
 * Único lugar del frontend donde vive el conjunto de tamaños de página permitidos.
 *
 * Tiene que coincidir con `cartera.constants.PAGE_SIZES_PERMITIDOS` del backend, que valida lo
 * mismo del lado servidor (ver `.claude/rules/dashboards.md`: un `page_size` fuera del conjunto
 * cae a 10 sin error, en los dos lados). Estaba escrito literal en cuatro archivos distintos
 * (`Pagination.jsx`, `ComponentPropertiesPanel.jsx`, `DetalleTable.jsx` y
 * `RecuperadorCausalMatrix.jsx`), es decir cinco fuentes de verdad contando el backend: cambiar el
 * conjunto exigía acordarse de los cinco y cualquier olvido pasaba desapercibido.
 */
export const PAGE_SIZES_PERMITIDOS = [5, 10, 25, 50, 100]

/** Tamaño al que se cae cuando el valor recibido no está en el conjunto. */
export const PAGE_SIZE_POR_DEFECTO = 10
