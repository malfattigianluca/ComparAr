export function getGenericCategory(raw: string | null, productName?: string): string {
    const c = (raw || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    const n = (productName || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');

    // ---- Carnes & Pescados (check FIRST, before Frescos) ----
    if (/bovin|carne|porc|avicol|pollo|milanesa|granja|pescad|mariscos|fiambre|embutid/.test(c)) return 'Carnes';
    if (/carnes-y-pescados/.test(c)) return 'Carnes';
    // Name-based fallback ONLY when category is generic/unknown (not snacks, almacen, etc.)
    if (!c || /^(frescos?|congelados?)$/.test(c)) {
        if (/\basado\b|\bbife\b|\bnalga\b|\bpicada\b|\bcostilla\b|\bvacio\b|\bmatambre\b|\bchorizo\b|\bmilanesa\b/.test(n)) return 'Carnes';
    }

    // ---- Lácteos ----
    if (/lacteo|leche|yogur|queso|manteca|crema|lacteos-y-productos/.test(c)) return 'Lácteos';
    if (/leche|yogur|queso|manteca/.test(n) && !/dulce de leche/.test(n)) return 'Lácteos';

    // ---- Bebidas ----
    if (/bebida|gaseosa|agua|vino|cerveza|jugo|soda|whisky|vodka|gin |aperitivo|espumante/.test(c)) return 'Bebidas';

    // ---- Verduras & Frutas ----
    if (/fruta|verdura|hortaliza|papa|cebolla|tomate|zanahoria|banana|naranja|manzana/.test(c)) return 'Frutas y Verduras';
    if (/frutas-y-verduras/.test(c)) return 'Frutas y Verduras';

    // ---- Frescos / Congelados (catch-all for "frescos" that didn't match above) ----
    if (/fresco|congelado|refrigerad/.test(c)) return 'Frescos';

    // ---- Panadería ----
    if (/panaderia|panader|reposteria|galletita|pan |dona|alfajor/.test(c)) return 'Panadería';
    if (/desayuno|merienda/.test(c)) return 'Desayuno';

    // ---- Limpieza ----
    if (/limpieza|detergente|lavandina|jabon|esponja|papel higienico|desinfectante/.test(c)) return 'Limpieza';

    // ---- Perfumería / Cuidado ----
    if (/perfumeria|cuidado|farmacia|bebe|salud|belleza|higiene|mundo-bebe/.test(c)) return 'Perfumería';

    // ---- Hogar / Bazar ----
    if (/hogar|bazar|electro|tecnolog|mascota|juguet|auto|librer|aire-libre|jardin|cuchillo|cubierto|utensilio/.test(c)) return 'Hogar';

    // ---- Almacén (default) ----
    if (/almacen|alimentos|aceite|arroz|harina|azucar|sal |snack|especialidad/.test(c)) return 'Almacén';

    return 'Otros';
}
