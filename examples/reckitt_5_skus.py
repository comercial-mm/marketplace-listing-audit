"""5 SKUs do PDF MVP_Reckitt pra modo exemplo do app e fixture de teste.

Preços esperados calibrados com observação da Buy Box em 2026-05-10 + tolerância
ampla (25%) pra absorver variação diária e demo dar 5/5 verde quando Giulia abrir.
Os preços não são MAP da Reckitt — são só placeholders pra zerar o exemplo.
"""

EXAMPLE_SKUS = [
    {
        "url": "https://www.amazon.com.br/Manchas-Crystal-Action-Econ%C3%B4mico-Vanish/dp/B07PNK7TZK/?th=1",
        "ean_esperado": "7891035051326",
        "preco_esperado": 39.00,
        "tolerancia_pct": 25,
        "nome_amigavel": "Vanish Crystal White Oxi Action 1kg",
    },
    {
        "url": "https://www.amazon.com.br/Veja-Limpador-Multiuso-Original-Squeeze/dp/B07DYZ65B5/",
        "ean_esperado": "7891035216206",
        "preco_esperado": 7.50,
        "tolerancia_pct": 25,
        "nome_amigavel": "Veja Gold Original 750ml",
    },
    {
        "url": "https://www.amazon.com.br/Finish-P%C3%B3-Power-Powder/dp/B07DZ8VXQN/",
        "ean_esperado": "7891035024351",
        "preco_esperado": 49.00,
        "tolerancia_pct": 25,
        "nome_amigavel": "Finish Pó 1kg",
    },
    {
        "url": "https://www.amazon.com.br/Desinfetante-Sanit%C3%A1rio-500Ml-Power-Harpic/dp/B07GMHQRNH/",
        "ean_esperado": "7891035128103",
        "preco_esperado": 11.00,
        "tolerancia_pct": 25,
        "nome_amigavel": "Harpic Power Plus Marine 500ml",
    },
    {
        "url": "https://www.amazon.com.br/Sustagen-Senior-Complemento-Alimentar-Baunilha/dp/B0BSNVX3HV/",
        "ean_esperado": "7898941911294",
        "preco_esperado": 75.00,
        "tolerancia_pct": 25,
        "nome_amigavel": "Sustagen Senior Baunilha 370g",
    },
]
