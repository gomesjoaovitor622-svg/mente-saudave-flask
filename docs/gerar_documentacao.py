"""Gera o diagrama de arquitetura e o PDF de documentacao do projeto.

Uso:
    python docs/gerar_documentacao.py

Requisitos: reportlab e Pillow (presentes em requirements-dev.txt).
"""

from pathlib import Path

from PIL import Image as PILImage
from PIL import ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.platypus import (
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    XPreformatted,
)
from reportlab.platypus.tableofcontents import TableOfContents

BASE = Path(__file__).resolve().parent
IMG_DIR = BASE / "img"
PDF_PATH = BASE / "Documentacao_Mente_Saudavel.pdf"

TEAL = colors.HexColor("#1d6b64")
TEAL_DARK = colors.HexColor("#123c3a")
TEAL_LIGHT = colors.HexColor("#e6f3f1")
GRAY = colors.HexColor("#64748b")
LINE = colors.HexColor("#dfe7e6")
INK = colors.HexColor("#1f2a37")

ARIAL = "C:/Windows/Fonts/arial.ttf"
ARIAL_BOLD = "C:/Windows/Fonts/arialbd.ttf"
ARIAL_ITALIC = "C:/Windows/Fonts/ariali.ttf"

pdfmetrics.registerFont(TTFont("Arial", ARIAL))
pdfmetrics.registerFont(TTFont("Arial-Bold", ARIAL_BOLD))
pdfmetrics.registerFont(TTFont("Arial-Italic", ARIAL_ITALIC))
pdfmetrics.registerFontFamily(
    "Arial",
    normal="Arial",
    bold="Arial-Bold",
    italic="Arial-Italic",
    boldItalic="Arial-Bold",
)


# ---------------------------------------------------------------------------
# Diagrama de arquitetura
# ---------------------------------------------------------------------------
def _font(size: int, bold: bool = False):
    path = ARIAL_BOLD if bold else ARIAL
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def _wrap(draw, text: str, font, max_width: int) -> list[str]:
    words = text.split()
    lines, current = [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=font) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _box(draw, xy, fill, outline, radius=18, width=3):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def _arrow(draw, start, end, color, width=4):
    draw.line([start, end], fill=color, width=width)
    x1, y1 = start
    x2, y2 = end
    dx, dy = x2 - x1, y2 - y1
    length = max((dx**2 + dy**2) ** 0.5, 1)
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    tip = (x2, y2)
    base = (x2 - ux * 18, y2 - uy * 18)
    p1 = (base[0] + px * 9, base[1] + py * 9)
    p2 = (base[0] - px * 9, base[1] - py * 9)
    draw.polygon([tip, p1, p2], fill=color)


def build_diagram() -> Path:
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    width, height = 1600, 900
    image = PILImage.new("RGB", (width, height), "#f7faf9")
    draw = ImageDraw.Draw(image)

    title_font = _font(42, bold=True)
    subtitle_font = _font(22)
    box_title = _font(27, bold=True)
    item_font = _font(20)
    label_font = _font(19, bold=True)

    draw.text((80, 45), "Arquitetura da solução", font=title_font, fill="#123c3a")
    draw.text(
        (80, 100),
        "Painel web e Postman consomem a API Flask, que persiste os dados no PostgreSQL.",
        font=subtitle_font,
        fill="#5d6b7a",
    )

    # Cliente
    client = (70, 220, 430, 640)
    _box(draw, client, "#eef7f5", "#24857c")
    draw.text((105, 250), "CLIENTE", font=box_title, fill="#1d6b64")
    client_items = [
        "Painel web (HTML, CSS e JS)",
        "Consumo via fetch / JSON",
        "Postman para testar a API",
        "Validação no front-end",
    ]
    y = 315
    for item in client_items:
        draw.text((105, y), "•", font=item_font, fill="#24857c")
        draw.text((130, y), item, font=item_font, fill="#1f2a37")
        y += 52

    # API
    api = (600, 185, 1010, 700)
    _box(draw, api, "#ffffff", "#24857c", width=4)
    draw.text((635, 215), "API FLASK", font=box_title, fill="#1d6b64")
    draw.text((635, 255), "Python 3 + Flask 3", font=_font(19), fill="#5d6b7a")
    api_items = [
        "Rotas REST (blueprints)",
        "Validações de CPF, e-mail e datas",
        "Stored procedures via psycopg2",
        "Erros padronizados em JSON",
        "Configuração centralizada (.env)",
        "Testes automatizados (pytest)",
    ]
    y = 320
    for item in api_items:
        draw.text((635, y), "•", font=item_font, fill="#b7791f")
        draw.text((660, y), item, font=item_font, fill="#1f2a37")
        y += 52

    # Banco
    db = (1180, 220, 1530, 640)
    _box(draw, db, "#f4f1fb", "#7c6bb0")
    draw.text((1215, 250), "POSTGRESQL", font=box_title, fill="#64539b")
    db_items = [
        "Tabelas normalizadas",
        "PK, FK e CHECK constraints",
        "Views com JOIN",
        "Stored procedures",
        "Triggers de auditoria",
        "Índices de desempenho",
    ]
    y = 315
    for item in db_items:
        draw.text((1215, y), "•", font=item_font, fill="#7c6bb0")
        draw.text((1240, y), item, font=item_font, fill="#1f2a37")
        y += 52

    # Setas
    _arrow(draw, (430, 430), (600, 430), "#1d6b64")
    draw.text((447, 385), "HTTP + JSON", font=label_font, fill="#1d6b64")
    draw.text((447, 448), "fetch / Postman", font=_font(17), fill="#5d6b7a")

    _arrow(draw, (1010, 430), (1180, 430), "#7c6bb0")
    draw.text((1032, 385), "SQL", font=label_font, fill="#64539b")
    draw.text((1032, 448), "psycopg2", font=_font(17), fill="#5d6b7a")

    # Rodape
    draw.line([(80, 760), (1520, 760)], fill="#dfe7e6", width=2)
    draw.text(
        (80, 785),
        "Camadas: apresentação  →  API REST  →  acesso a dados (psycopg2)  →  persistência (PostgreSQL)",
        font=_font(21),
        fill="#334155",
    )
    draw.text(
        (80, 830),
        "Projeto integrador — Desenvolvimento Web III + Banco de Dados II — IFRO, 2026",
        font=_font(18),
        fill="#64748b",
    )

    path = IMG_DIR / "arquitetura.png"
    image.save(path)
    return path


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------
def _styles():
    base = getSampleStyleSheet()
    return {
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName="Arial",
            fontSize=10.5,
            leading=15.5,
            alignment=TA_JUSTIFY,
            textColor=INK,
            spaceAfter=8,
        ),
        "h1": ParagraphStyle(
            "H1",
            parent=base["Heading1"],
            fontName="Arial-Bold",
            fontSize=15.5,
            leading=20,
            textColor=TEAL_DARK,
            spaceBefore=14,
            spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontName="Arial-Bold",
            fontSize=12,
            leading=16,
            textColor=TEAL,
            spaceBefore=12,
            spaceAfter=6,
        ),
        "caption": ParagraphStyle(
            "Caption",
            parent=base["BodyText"],
            fontName="Arial-Italic",
            fontSize=8.5,
            leading=12,
            alignment=TA_CENTER,
            textColor=GRAY,
            spaceBefore=4,
            spaceAfter=14,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=base["BodyText"],
            fontName="Arial",
            fontSize=8,
            leading=11,
            textColor=INK,
        ),
        "cell": ParagraphStyle(
            "Cell",
            parent=base["BodyText"],
            fontName="Arial",
            fontSize=8,
            leading=10.5,
            textColor=INK,
        ),
        "cell_bold": ParagraphStyle(
            "CellBold",
            parent=base["BodyText"],
            fontName="Arial-Bold",
            fontSize=8,
            leading=10.5,
            textColor=INK,
        ),
        "cover_title": ParagraphStyle(
            "CoverTitle",
            parent=base["Title"],
            fontName="Arial-Bold",
            fontSize=32,
            leading=38,
            alignment=TA_CENTER,
            textColor=TEAL_DARK,
            spaceAfter=6,
        ),
        "cover_sub": ParagraphStyle(
            "CoverSub",
            parent=base["BodyText"],
            fontName="Arial",
            fontSize=14,
            leading=20,
            alignment=TA_CENTER,
            textColor=GRAY,
        ),
        "cover_name": ParagraphStyle(
            "CoverName",
            parent=base["BodyText"],
            fontName="Arial-Bold",
            fontSize=13,
            leading=18,
            alignment=TA_CENTER,
            textColor=TEAL_DARK,
        ),
    }


def _p(text: str, style) -> Paragraph:
    return Paragraph(text, style)


def _table(rows, col_widths, styles, header=True, font_size=8):
    data = []
    for index, row in enumerate(rows):
        style = styles["cell_bold"] if header and index == 0 else styles["cell"]
        data.append([_p(str(cell), style) for cell in row])

    table = Table(data, colWidths=col_widths, repeatRows=1 if header else 0)
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        commands += [
            ("BACKGROUND", (0, 0), (-1, 0), TEAL_LIGHT),
            ("TEXTCOLOR", (0, 0), (-1, 0), TEAL_DARK),
        ]
    table.setStyle(TableStyle(commands))
    return table


def _image_block(path: Path, caption: str, styles, max_width=16.5 * cm, max_height=20.5 * cm):
    if not path.exists():
        return []
    with PILImage.open(path) as image:
        px_width, px_height = image.size
    ratio = min(max_width / px_width, max_height / px_height)
    flow = Image(str(path), width=px_width * ratio, height=px_height * ratio)
    flow.hAlign = "CENTER"
    return [KeepTogether([flow, _p(caption, styles["caption"])])]


def _bullets(items, styles):
    return ListFlowable(
        [ListItem(_p(item, styles["body"]), leftIndent=12) for item in items],
        bulletType="bullet",
        start="•",
        leftIndent=14,
        bulletFontName="Arial",
        bulletFontSize=8,
        spaceAfter=4,
    )


def _public_url() -> str:
    """Le a URL publica da demonstracao, se o tunel ja tiver sido iniciado.

    O script que sobe o Cloudflare grava o endereco em docs/URL_PUBLICA.txt.
    Quando o arquivo nao existe (execucao offline), devolve um placeholder
    explicito para que a documentacao nunca exiba um link quebrado.
    """
    path = BASE / "URL_PUBLICA.txt"
    if path.exists():
        url = path.read_text(encoding="utf-8").strip()
        if url:
            return url
    return "https://&lt;subdominio&gt;.trycloudflare.com (link temporario)"


class DocComSumario(SimpleDocTemplate):
    """Documento que registra os títulos H1/H2 para montar o sumário.

    O ``multiBuild`` executa a montagem duas vezes: na primeira descobre em que
    página cada título caiu; na segunda preenche o ``TableOfContents`` com os
    números corretos. Sem isso, o sumário ficaria com páginas erradas.
    """

    def afterFlowable(self, flowable):
        if not isinstance(flowable, Paragraph):
            return
        style = flowable.style.name
        if style not in {"H1", "H2"}:
            return
        text = flowable.getPlainText()
        if text.strip().lower() == "sumário":
            return
        level = 0 if style == "H1" else 1
        self.notify("TOCEntry", (level, text, self.page))


class CanvasNumerado(pdfcanvas.Canvas):
    """Canvas que imprime "Página X de Y" no rodapé de todas as páginas."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._estados = []

    def showPage(self):
        self._estados.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._estados)
        for estado in self._estados:
            self.__dict__.update(estado)
            self._imprime_numero(total)
            super().showPage()
        super().save()

    def _imprime_numero(self, total: int):
        self.saveState()
        self.setFont("Arial", 8)
        self.setFillColor(GRAY)
        self.drawCentredString(
            A4[0] / 2, 1.1 * cm, f"Página {self._pageNumber} de {total}"
        )
        self.restoreState()


def build_pdf():
    styles = _styles()
    doc = DocComSumario(
        str(PDF_PATH),
        pagesize=A4,
        leftMargin=2.1 * cm,
        rightMargin=2.1 * cm,
        topMargin=2.0 * cm,
        bottomMargin=1.8 * cm,
        title="Documentação — Mente Saudável",
        author="Jhennyfér e João Vitor — IFRO",
        subject="Projeto integrador de Desenvolvimento Web III e Banco de Dados II",
    )

    def on_page(canvas, document):
        canvas.saveState()
        if document.page > 1:
            canvas.setFont("Arial", 7.5)
            canvas.setFillColor(GRAY)
            canvas.drawString(
                2.1 * cm,
                A4[1] - 1.35 * cm,
                "Mente Saudável — Documentação do sistema",
            )
            canvas.drawRightString(A4[0] - 2.1 * cm, A4[1] - 1.35 * cm, "IFRO · 2026")
            canvas.setStrokeColor(LINE)
            canvas.setLineWidth(0.6)
            canvas.line(2.1 * cm, A4[1] - 1.55 * cm, A4[0] - 2.1 * cm, A4[1] - 1.55 * cm)
        canvas.restoreState()

    story = []

    # ------------------------------ Capa -----------------------------------
    story += [
        Spacer(1, 1.4 * cm),
        _p("INSTITUTO FEDERAL DE EDUCAÇÃO, CIÊNCIA E TECNOLOGIA DE RONDÔNIA", styles["cell_bold"]),
        Spacer(1, 0.2 * cm),
        _p("Curso Superior de Tecnologia em Sistemas para Internet", styles["small"]),
        Spacer(1, 3.0 * cm),
        _p("Mente Saudável", styles["cover_title"]),
        _p("Sistema de gestão para clínica de psicologia", styles["cover_sub"]),
        Spacer(1, 0.6 * cm),
        _p("Documentação do projeto integrador", styles["cover_sub"]),
        Spacer(1, 3.0 * cm),
    ]

    cover_data = [
        ["Disciplinas", "Desenvolvimento Web III + Banco de Dados II"],
        ["Turma", "2025.1"],
        ["Tecnologias", "Python, Flask, PostgreSQL, HTML, CSS e JavaScript"],
        ["Ano", "2026"],
    ]
    cover_table = _table(cover_data, [4.2 * cm, 10.5 * cm], styles, header=False)
    cover_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.4, LINE),
                ("BACKGROUND", (0, 0), (0, -1), TEAL_LIGHT),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story += [cover_table, Spacer(1, 2.2 * cm)]

    story += [
        _p("Integrantes", styles["cell_bold"]),
        Spacer(1, 0.25 * cm),
        _p("Jhennyfér", styles["cover_name"]),
        Spacer(1, 0.2 * cm),
        _p("João Vitor", styles["cover_name"]),
        Spacer(1, 0.9 * cm),
        _p(
            "Dupla responsável pelo desenvolvimento do projeto integrador.",
            styles["caption"],
        ),
        PageBreak(),
    ]

    # ------------------------------ Sumário --------------------------------
    story.append(_p("Sumário", styles["h1"]))
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle(
            "TOC1",
            fontName="Arial-Bold",
            fontSize=10.5,
            leading=15,
            textColor=TEAL_DARK,
            leftIndent=0,
            firstLineIndent=0,
            spaceBefore=2,
        ),
        ParagraphStyle(
            "TOC2",
            fontName="Arial",
            fontSize=9.5,
            leading=13,
            textColor=INK,
            leftIndent=14,
            firstLineIndent=0,
        ),
    ]
    story += [toc, PageBreak()]

    # ---------------------------- 1. Introducao ----------------------------
    story.append(_p("1. Introdução", styles["h1"]))
    story.append(
        _p(
            "O projeto <b>Mente Saudável</b> consiste em uma Web API REST desenvolvida "
            "em Python com o microframework Flask, integrada a um banco de dados "
            "PostgreSQL. O sistema apoia a rotina de uma clínica de psicologia, "
            "permitindo gerenciar pacientes, profissionais, consultas e evoluções "
            "clínicas, além de gerar relatórios de atendimento.",
            styles["body"],
        )
    )
    story.append(
        _p(
            "A solução aplica conceitos de normalização, integridade referencial, "
            "check constraints, stored procedures, views com JOIN, triggers e troca "
            "de mensagens no formato JSON, conforme os requisitos das disciplinas "
            "Desenvolvimento Web III e Banco de Dados II.",
            styles["body"],
        )
    )

    story.append(_p("2. Objetivo", styles["h1"]))
    story.append(
        _p(
            "Desenvolver uma aplicação web com API REST capaz de realizar operações "
            "CRUD sobre os cadastros da clínica, persistindo os dados em um banco "
            "relacional bem estruturado, com validações no front-end, no back-end e "
            "no próprio banco, além de disponibilizar relatórios construídos a partir "
            "de views e stored procedures.",
            styles["body"],
        )
    )

    story.append(_p("3. Descrição do sistema", styles["h1"]))
    story.append(
        _p(
            "O sistema é composto por quatro módulos principais, todos acessíveis pela "
            "API e pelo painel web:",
            styles["body"],
        )
    )
    story.append(
        _bullets(
            [
                "<b>Pacientes:</b> CRUD completo, busca por nome, filtro por status e "
                "resumo individual com total de consultas, consultas realizadas, "
                "consultas agendadas, humor médio e última consulta.",
                "<b>Psicólogos:</b> cadastro com CRP, especialidade, valor padrão da "
                "sessão e situação (ativo/inativo).",
                "<b>Consultas:</b> agendamento com verificação de conflito de horário, "
                "modalidade (presencial ou online), duração, valor e status.",
                "<b>Evoluções:</b> prontuário de cada consulta, com nota de humor (1 a "
                "10), relato clínico e encaminhamento.",
            ],
            styles,
        )
    )
    story.append(
        _p(
            "O painel web exibe indicadores gerais, próximas consultas, distribuição "
            "de atendimentos por especialidade e tabelas com ações de cadastro, edição "
            "e exclusão.",
            styles["body"],
        )
    )

    # ---------------------------- 4. Arquitetura ---------------------------
    story.append(PageBreak())
    story.append(_p("4. Arquitetura da solução", styles["h1"]))
    story.append(
        _p(
            "A figura a seguir sintetiza a arquitetura: o cliente (painel web ou "
            "Postman) envia requisições HTTP com JSON para a API Flask, que valida os "
            "dados, executa a lógica de negócio e acessa o PostgreSQL por meio do "
            "driver psycopg2.",
            styles["body"],
        )
    )
    story += _image_block(
        IMG_DIR / "arquitetura.png",
        "Figura 1 — Arquitetura da solução em camadas.",
        styles,
        max_height=12.5 * cm,
    )
    story.append(
        _p(
            "A API está organizada em blueprints (pacientes, psicólogos, consultas, "
            "evoluções, relatórios e health check), com validações reutilizáveis, "
            "tratamento centralizado de erros e configuração centralizada em um "
            "arquivo <font name='Courier'>.env</font>. O acesso ao banco fica isolado "
            "no módulo <font name='Courier'>app/db.py</font>.",
            styles["body"],
        )
    )

    story.append(_p("4.1 Estrutura do repositório", styles["h2"]))
    repo_tree = """mente-saudave-flask/
├── app/                 # API Flask (blueprints, validação, acesso ao banco)
│   ├── routes/          # pacientes, psicólogos, consultas, evoluções, relatórios
│   ├── static/          # CSS e JavaScript do painel
│   └── templates/       # index.html (painel web)
├── database/            # 00_create_database, 01_schema, 02_views, 03_procedures, 04_seed
├── docs/                # PDF, relatório de testes, gerador e imagens
├── postman/             # coleção da API
├── scripts/             # relatório de testes, geração e verificação do ZIP
├── tests/               # validadores, API e integridade do banco
├── app.py               # ponto de entrada oficial
├── run.py               # compatibilidade (delega para app.py)
├── requirements.txt
└── README.md"""
    story.append(
        XPreformatted(
            repo_tree,
            ParagraphStyle(
                "Tree",
                fontName="Courier",
                fontSize=7.2,
                leading=9.4,
                textColor=colors.HexColor("#334155"),
                backColor=colors.HexColor("#f8fafc"),
                borderColor=LINE,
                borderWidth=0.5,
                borderPadding=6,
                spaceAfter=8,
            ),
        )
    )

    # --------------------------- 5. Modelo de dados ------------------------
    story.append(_p("5. Modelo de dados", styles["h1"]))
    story.append(
        _p(
            "O banco foi modelado seguindo a normalização (3ª forma normal), evitando "
            "redundância. A tabela de evoluções referencia apenas a consulta; os dados "
            "do paciente e do psicólogo são obtidos por JOIN.",
            styles["body"],
        )
    )

    story.append(_p("5.1 Tabelas, chaves e restrições", styles["h2"]))
    story.append(
        _table(
            [
                ["Tabela", "Chave primária", "Chaves estrangeiras", "Principais regras"],
                [
                    "psicologos",
                    "id_psicologo",
                    "—",
                    "CRP único (formato UF/número); e-mail válido; valor da sessão > 0",
                ],
                [
                    "pacientes",
                    "id_paciente",
                    "—",
                    "CPF único com 11 dígitos; e-mail válido; nascimento não futuro; status ativo/inativo",
                ],
                [
                    "consultas",
                    "id_consulta",
                    "id_paciente → pacientes; id_psicologo → psicologos",
                    "Duração entre 15 e 180 min; modalidade e status restritos; valor ≥ 0",
                ],
                [
                    "evolucoes",
                    "id_evolucao",
                    "id_consulta → consultas (única)",
                    "Humor entre 1 e 10; relato com no mínimo 10 caracteres",
                ],
                [
                    "auditoria_pacientes",
                    "id_auditoria",
                    "—",
                    "Registra INSERT/UPDATE/DELETE com snapshots em JSONB",
                ],
            ],
            [2.6 * cm, 2.6 * cm, 4.4 * cm, 7.0 * cm],
            styles,
        )
    )
    story.append(Spacer(1, 0.25 * cm))

    story.append(_p("5.2 Check constraints", styles["h2"]))
    story.append(
        _p(
            "Foram implementadas 18 check constraints nomeadas, entre elas: "
            "<font name='Courier'>ck_pacientes_cpf_formato</font> (CPF com 11 "
            "dígitos), <font name='Courier'>ck_pacientes_nascimento</font> (data entre "
            "1900 e a data atual), <font name='Courier'>ck_pacientes_status</font>, "
            "<font name='Courier'>ck_psicologos_crp_formato</font>, "
            "<font name='Courier'>ck_psicologos_valor_positivo</font>, "
            "<font name='Courier'>ck_consultas_duracao</font> (15 a 180 minutos), "
            "<font name='Courier'>ck_consultas_modalidade</font>, "
            "<font name='Courier'>ck_evolucoes_humor</font> (1 a 10) e "
            "<font name='Courier'>ck_evolucoes_relato_minimo</font>. Um índice único "
            "parcial impede dois agendamentos ativos no mesmo horário para o mesmo "
            "psicólogo, liberando o horário quando a consulta é cancelada.",
            styles["body"],
        )
    )

    story.append(_p("5.3 Objetos do banco de dados", styles["h2"]))
    story.append(
        _table(
            [
                ["Objeto", "Qtd.", "Observação"],
                ["Tabelas", "5", "psicologos, pacientes, consultas, evolucoes e auditoria_pacientes"],
                ["CHECK constraints", "18", "CPF, CRP, datas, status, duração, modalidade, humor e relato mínimo"],
                ["Chaves estrangeiras", "3", "duas em consultas e uma em evolucoes"],
                ["Views", "3", "agenda completa, evoluções e relatório de atendimentos"],
                ["Stored procedures", "4", "cadastro, agendamento, evolução e relatório com REFCURSOR"],
                ["Funções", "2", "resumo do paciente e relatório em formato tabular"],
                ["Triggers", "2", "auditoria de pacientes em INSERT/UPDATE/DELETE"],
                ["Índices", "6", "inclui o índice único parcial que evita double-booking"],
            ],
            [3.6 * cm, 1.6 * cm, 11.4 * cm],
            styles,
        )
    )
    story.append(Spacer(1, 0.25 * cm))

    story.append(_p("5.4 Comentários das colunas no script do banco", styles["h2"]))
    story.append(
        _p(
            "Conforme exigido, o script <font name='Courier'>database/01_schema.sql</font> "
            "descreve cada coluna em comentário ao lado da definição:",
            styles["body"],
        )
    )
    sql_excerpt = """CREATE TABLE pacientes (
    id_paciente     SERIAL        PRIMARY KEY,
    nome            VARCHAR(120)  NOT NULL,                          -- Nome completo do paciente
    cpf             CHAR(11)      NOT NULL UNIQUE,                   -- CPF sem pontuacao (11 digitos)
    email           VARCHAR(160)  NOT NULL UNIQUE,                   -- E-mail de contato do paciente
    telefone        VARCHAR(20),                                     -- Telefone com DDD (opcional)
    data_nascimento DATE          NOT NULL,                          -- Data de nascimento do paciente
    genero          VARCHAR(20)   NOT NULL DEFAULT 'nao_informado',  -- Genero declarado pelo paciente
    cidade          VARCHAR(80),                                     -- Cidade onde o paciente reside
    observacoes     TEXT,                                            -- Observacoes gerais do cadastro
    status          VARCHAR(15)   NOT NULL DEFAULT 'ativo',          -- Situacao do cadastro
    criado_em       TIMESTAMPTZ   NOT NULL DEFAULT now(),            -- Data/hora de cadastro
    atualizado_em   TIMESTAMPTZ,                                     -- Ultima alteracao
    ...
);"""
    story.append(
        XPreformatted(
            sql_excerpt,
            ParagraphStyle(
                "Code",
                fontName="Courier",
                fontSize=6.9,
                leading=9.2,
                textColor=colors.HexColor("#334155"),
                backColor=colors.HexColor("#f8fafc"),
                borderColor=LINE,
                borderWidth=0.5,
                borderPadding=6,
                spaceBefore=4,
                spaceAfter=8,
            ),
        )
    )

    # ---------------------- 6. Procedures e views --------------------------
    story.append(PageBreak())
    story.append(_p("6. Stored procedures e views", styles["h1"]))
    story.append(
        _table(
            [
                ["Objeto", "Tipo", "Uso"],
                ["sp_criar_paciente", "procedure", "Chamada em POST /api/pacientes; valida CPF/e-mail duplicados e idade mínima"],
                ["sp_agendar_consulta", "procedure", "Chamada em POST /api/consultas; valida paciente, psicólogo e conflito de horário"],
                ["sp_registrar_evolucao", "procedure", "Chamada em POST /api/evolucoes; uma evolução por consulta"],
                ["sp_relatorio_atendimentos", "procedure", "Relatório por período com REFCURSOR, lendo a view de atendimentos"],
                ["vw_agenda_completa", "view", "Consultas + pacientes + psicólogos (JOIN de três tabelas)"],
                ["vw_evolucoes", "view", "Prontuário com dados do paciente e do profissional"],
                ["vw_relatorio_atendimentos", "view", "Base do relatório, com LEFT JOIN em evoluções"],
                ["fn_resumo_paciente", "function", "Totais de consultas e humor médio por paciente"],
                ["fn_relatorio_atendimentos", "function", "Versão tabular do relatório, consumida pela API"],
            ],
            [4.6 * cm, 2.3 * cm, 9.7 * cm],
            styles,
        )
    )
    story.append(Spacer(1, 0.3 * cm))
    story.append(
        _p(
            "A procedure de relatório atende ao requisito de utilizar uma <b>view com "
            "JOIN</b> e não é chamada pela API. Exemplo de uso no PostgreSQL:",
            styles["body"],
        )
    )
    call_excerpt = """BEGIN;
CALL sp_relatorio_atendimentos(CURRENT_DATE - 30, CURRENT_DATE, 'relatorio');
FETCH ALL FROM relatorio;
COMMIT;"""
    story.append(
        XPreformatted(
            call_excerpt,
            ParagraphStyle(
                "Code2",
                fontName="Courier",
                fontSize=8,
                leading=11,
                textColor=colors.HexColor("#334155"),
                backColor=colors.HexColor("#f8fafc"),
                borderColor=LINE,
                borderWidth=0.5,
                borderPadding=7,
                spaceAfter=10,
            ),
        )
    )

    # --------------------------- 7. Endpoints ------------------------------
    story.append(_p("7. Endpoints da API", styles["h1"]))
    story.append(
        _p(
            "Todos os dados trafegam em JSON. A tabela abaixo resume as rotas "
            "disponíveis (a coleção do Postman acompanha o projeto).",
            styles["body"],
        )
    )
    story.append(
        _table(
            [
                ["Método", "Rota", "Descrição"],
                ["GET", "/api/health", "Verifica API e conexão com o banco"],
                ["GET", "/api/pacientes", "Lista paginada (nome, status, cidade)"],
                ["GET", "/api/pacientes/{id}", "Busca paciente por id"],
                ["GET", "/api/pacientes/{id}/resumo", "Resumo individual do paciente"],
                ["POST", "/api/pacientes", "Cadastra paciente (stored procedure)"],
                ["PUT", "/api/pacientes/{id}", "Atualiza paciente"],
                ["DELETE", "/api/pacientes/{id}", "Remove paciente"],
                ["GET / POST", "/api/psicologos", "Lista / cadastra psicólogos"],
                ["GET / PUT / DELETE", "/api/psicologos/{id}", "Consulta / atualiza / remove psicólogo"],
                ["GET", "/api/consultas", "Lista consultas com filtros"],
                ["POST", "/api/consultas", "Agenda consulta (stored procedure)"],
                ["GET / PUT / DELETE", "/api/consultas/{id}", "Consulta / atualiza / remove consulta"],
                ["GET", "/api/evolucoes", "Lista evoluções"],
                ["POST", "/api/evolucoes", "Registra evolução (stored procedure)"],
                ["GET / PUT / DELETE", "/api/evolucoes/{id}", "Consulta / atualiza / remove evolução"],
                ["GET", "/api/relatorios/atendimentos", "Relatório por período"],
                ["GET", "/api/relatorios/resumo", "Indicadores gerais"],
            ],
            [3.1 * cm, 6.0 * cm, 7.5 * cm],
            styles,
        )
    )
    story.append(Spacer(1, 0.3 * cm))
    story.append(
        _p(
            "Formato padronizado de erro: "
            "<font name='Courier'>{ \"erro\": true, \"mensagem\": \"...\", \"status\": 422 }</font>.",
            styles["body"],
        )
    )

    story.append(_p("7.1 Segurança e boas práticas", styles["h2"]))
    story.append(
        _bullets(
            [
                "<b>Credenciais fora do código:</b> host, porta, usuário e senha vêm de variáveis de ambiente (<font name='Courier'>.env</font>), que não é versionado.",
                "<b>Consultas parametrizadas:</b> todos os valores passam por <font name='Courier'>%s</font> no psycopg2, eliminando SQL injection; o nome da procedure é constante no código.",
                "<b>Validação em três camadas:</b> front-end, API (CPF, e-mail, datas, enums) e banco (CHECK, UNIQUE, FK e triggers).",
                "<b>Erros sem vazamento:</b> detalhes técnicos do PostgreSQL vão para o log; o cliente recebe JSON padronizado com status semântico.",
                "<b>CORS e preflight:</b> o painel e o Postman podem consumir a API de outra origem; <font name='Courier'>OPTIONS</font> responde 204.",
                "<b>Conexão por requisição:</b> uma conexão por request em <font name='Courier'>flask.g</font>, fechada no <font name='Courier'>teardown</font>, evitando vazamento.",
                "<b>Integridade no banco:</b> constraints, índice único parcial e triggers garantem as regras mesmo fora da API.",
            ],
            styles,
        )
    )

    # ----------------------------- 8. Testes ------------------------------
    story.append(PageBreak())
    story.append(_p("8. Testes e evidências", styles["h1"]))
    story.append(
        _p(
            "A validação do sistema foi feita em três frentes complementares: "
            "(i) capturas do painel web; (ii) execução real dos endpoints com "
            "evidências no estilo Postman; e (iii) suíte automatizada com pytest. "
            "O relatório completo, com o payload, o status HTTP e o efeito no banco "
            "de cada requisição, está em "
            "<font name='Courier'>docs/RELATORIO_DE_TESTES.md</font>.",
            styles["body"],
        )
    )

    story.append(_p("8.1 Painel web", styles["h2"]))
    story += _image_block(
        IMG_DIR / "painel.png",
        "Figura 2 — Painel geral com indicadores, próximas consultas e distribuição por especialidade.",
        styles,
        max_width=16.0 * cm,
        max_height=10.5 * cm,
    )
    story += _image_block(
        IMG_DIR / "pacientes.png",
        "Figura 3 — Tela de pacientes com busca, status e ações de edição/exclusão.",
        styles,
        max_width=16.0 * cm,
        max_height=10.5 * cm,
    )

    story.append(PageBreak())
    story += _image_block(
        IMG_DIR / "agenda.png",
        "Figura 4 — Agenda de consultas com modalidade, valor e status.",
        styles,
        max_width=16.0 * cm,
        max_height=10.5 * cm,
    )

    # ------------------- 8.2 Evidencias no estilo Postman ------------------
    story.append(PageBreak())
    story.append(_p("8.2 Evidências dos testes da API", styles["h2"]))
    story.append(
        _p(
            "As figuras a seguir reproduzem as requisições reais executadas por "
            "<font name='Courier'>scripts/relatorio_testes.py</font> contra a API "
            "em execução. Cada cartão mostra o método, a URL, o corpo JSON enviado, "
            "o status HTTP e o JSON devolvido, além da verificação feita diretamente "
            "no PostgreSQL.",
            styles["body"],
        )
    )
    story += _image_block(
        IMG_DIR / "postman-pacientes.png",
        "Figura 5 — POST /api/pacientes: cadastro executado pela stored procedure "
        "sp_criar_paciente, com retorno 201 Created e verificação do registro no banco.",
        styles,
        max_width=16.5 * cm,
        max_height=12.6 * cm,
    )
    story += _image_block(
        IMG_DIR / "postman-pacientes-erro.png",
        "Figura 6 — Tentativa de cadastrar CPF duplicado: a procedure recusa a "
        "operação e a API responde 409 Conflict, sem inserir nova linha.",
        styles,
        max_width=16.5 * cm,
        max_height=10.4 * cm,
    )

    story.append(PageBreak())
    story += _image_block(
        IMG_DIR / "postman-consultas.png",
        "Figura 7 — POST /api/consultas: agendamento executado pela stored procedure "
        "sp_agendar_consulta, com retorno 201 Created.",
        styles,
        max_width=16.5 * cm,
        max_height=12.6 * cm,
    )
    story += _image_block(
        IMG_DIR / "postman-consultas-erro.png",
        "Figura 8 — Tentativa de double-booking: o índice único parcial e a procedure "
        "bloqueiam o segundo agendamento ativo no mesmo horário (409 Conflict).",
        styles,
        max_width=16.5 * cm,
        max_height=10.4 * cm,
    )

    story.append(PageBreak())
    story += _image_block(
        IMG_DIR / "postman-evolucoes.png",
        "Figura 9 — POST /api/evolucoes: registro do prontuário pela stored procedure "
        "sp_registrar_evolucao, garantindo uma evolução por consulta.",
        styles,
        max_width=16.5 * cm,
        max_height=12.6 * cm,
    )
    story += _image_block(
        IMG_DIR / "postman-constraints.png",
        "Figura 10 — Oito CHECK constraints testadas por SQL direto: o PostgreSQL "
        "rejeita todos os dados inválidos, mesmo sem passar pela API.",
        styles,
        max_width=16.5 * cm,
        max_height=10.4 * cm,
    )

    story.append(PageBreak())
    story += _image_block(
        IMG_DIR / "postman-listagem.png",
        "Figura 11 — GET /api/pacientes com filtro por nome: listagem paginada com "
        "metadados de paginação retornados pela API.",
        styles,
        max_width=16.5 * cm,
        max_height=13.5 * cm,
    )

    # --------------------- 8.3 Testes automatizados -----------------------
    story.append(_p("8.3 Testes automatizados", styles["h2"]))
    story.append(
        _p(
            "A suíte automatizada reúne <b>56 testes</b> distribuídos em "
            "<font name='Courier'>tests/test_validators.py</font> (validações "
            "unitárias), <font name='Courier'>tests/test_api.py</font> (integração "
            "dos endpoints) e <font name='Courier'>tests/test_constraints.py</font> "
            "(integridade do banco: CHECK, UNIQUE, FK, CASCADE, índice parcial, "
            "triggers, procedures, views e funções).",
            styles["body"],
        )
    )
    story.append(
        XPreformatted(
            "$ pytest -q\n"
            ".......................................................  [100%]\n"
            "56 passed in 5.66s",
            ParagraphStyle(
                "Code3",
                fontName="Courier",
                fontSize=8,
                leading=11,
                textColor=colors.HexColor("#334155"),
                backColor=colors.HexColor("#f8fafc"),
                borderColor=LINE,
                borderWidth=0.5,
                borderPadding=7,
                spaceAfter=10,
            ),
        )
    )

    # ---------------------- 8.4 Resumo dos resultados ---------------------
    story.append(_p("8.4 Resumo dos resultados", styles["h2"]))
    story.append(
        _table(
            [
                ["Verificação", "Resultado"],
                ["Testes HTTP executados contra a API real", "22 de 22 com o status esperado"],
                ["CHECK constraints testadas por SQL direto", "8 de 8 rejeitaram o dado inválido"],
                ["Suíte automatizada (pytest)", "56 testes aprovados"],
                ["Cobertura funcional", "CRUD, listagens, stored procedures, views e relatórios"],
                ["Efeito no banco", "Conferido por consulta direta após cada operação"],
            ],
            [9.0 * cm, 7.6 * cm],
            styles,
        )
    )

    # -------------------------- 9. Divisao de tarefas ----------------------
    story.append(PageBreak())
    story.append(_p("9. Divisão de tarefas", styles["h1"]))
    story.append(
        _p(
            "A dupla foi organizada em duas frentes de trabalho complementares. Cada "
            "entrega passa por revisão do outro integrante (duplo check), conforme "
            "orientação da atividade.",
            styles["body"],
        )
    )
    story.append(
        _table(
            [
                ["Integrante", "Banco de Dados II", "Desenvolvimento Web III", "Documentação e testes", "Revisão"],
                [
                    "Jhennyfér",
                    "Modelagem e normalização; 01_schema.sql; CHECK/FK/UNIQUE, triggers e índices; views com JOIN (02_views.sql) e funções de relatório",
                    "Apoio à camada de acesso (app/db.py) e às chamadas de procedures; tabela de endpoints e coleção do Postman",
                    "Comentários coluna a coluna, constraints e views; relatório de testes; PDF final e ZIP",
                    "João Vitor",
                ],
                [
                    "João Vitor",
                    "Stored procedures (03_procedures.sql) e dados de exemplo (04_seed.sql); testes de integridade (tests/test_constraints.py)",
                    "API Flask, blueprints, validações e tratamento de erros; painel web e integração via fetch; testes de API (tests/test_api.py)",
                    "Capturas de tela, evidências Postman e revisão do script SQL",
                    "Jhennyfér",
                ],
            ],
            [2.4 * cm, 4.0 * cm, 3.9 * cm, 3.9 * cm, 2.4 * cm],
            styles,
        )
    )
    story.append(Spacer(1, 0.3 * cm))

    # ---------------------------- 10. Execucao ----------------------------
    story.append(_p("10. Como executar e link de acesso", styles["h1"]))
    story.append(
        _bullets(
            [
                "No VS Code, abrir a pasta e executar uma única vez a tarefa <b>Projeto: primeiro uso</b>: ela cria o <font name='Courier'>.venv</font>, instala as dependências, cria o cluster PostgreSQL exclusivo do projeto na porta 55433 e gera o <font name='Courier'>.env</font>.",
                "Pressionar <b>F5</b> (configuração <b>API: depurar (Flask)</b>) ou executar a tarefa <b>API: executar</b>; o VS Code sobe o banco e o Flask juntos.",
                "Alternativamente, executar manualmente os scripts 00 a 04 da pasta <font name='Courier'>database/</font>, copiar <font name='Courier'>.env.example</font> para <font name='Courier'>.env</font> e rodar <font name='Courier'>python app.py</font>.",
                "Acessar <font name='Courier'>http://localhost:5000</font> e a lista de endpoints em <font name='Courier'>http://localhost:5000/api</font>.",
                "Disparar requisições pelo arquivo <font name='Courier'>api.http</font> (extensão REST Client) ou pela coleção do Postman.",
            ],
            styles,
        )
    )
    story.append(
        _p(
            "O arquivo <font name='Courier'>app.py</font> é o ponto de entrada oficial; "
            "<font name='Courier'>run.py</font> existe apenas por compatibilidade. "
            "As instruções completas, incluindo testes e Postman, estão no "
            "<font name='Courier'>README.md</font> do repositório.",
            styles["body"],
        )
    )
    story.append(
        _table(
            [
                ["Ambiente", "Endereço"],
                ["Local (desenvolvimento)", "http://localhost:5000"],
                ["Índice de endpoints", "http://localhost:5000/api"],
                ["API / health check", "http://localhost:5000/api/health"],
                ["Demonstração pública", _public_url()],
            ],
            [5.2 * cm, 11.4 * cm],
            styles,
        )
    )
    story.append(
        _p(
            "O link público é temporário: ele permanece ativo enquanto o servidor "
            "Flask, o PostgreSQL e o túnel Cloudflare estiverem em execução na "
            "máquina de demonstração.",
            styles["caption"],
        )
    )

    # --------------------- 11. Empacotamento e entrega ---------------------
    story.append(PageBreak())
    story.append(_p("11. Empacotamento e entrega (ZIP)", styles["h1"]))
    story.append(
        _p(
            "A entrega deve ser um único arquivo ZIP contendo o script SQL completo, "
            "o código-fonte organizado e o PDF de documentação. O nome do arquivo "
            "segue a regra da atividade:",
            styles["body"],
        )
    )
    story.append(
        XPreformatted(
            "[nome inicial de cada membro separado por _].[nome do sistema].zip",
            ParagraphStyle(
                "Code4",
                fontName="Courier-Bold",
                fontSize=9,
                leading=12,
                textColor=TEAL_DARK,
                backColor=TEAL_LIGHT,
                borderColor=TEAL,
                borderWidth=0.6,
                borderPadding=8,
                spaceAfter=8,
            ),
        )
    )
    story.append(
        _p(
            "Exemplo com quatro integrantes (João, Maria, Pedro e Ana): "
            "<font name='Courier'>Joao_Maria_Pedro_Ana.Mente_Saudavel.zip</font>. "
            "Para esta entrega, o pacote é "
            "<font name='Courier'>Jhennyfer_Joao.Mente_Saudavel.zip</font>. "
            "O script <font name='Courier'>scripts/gerar_zip.py</font> monta o pacote "
            "automaticamente e valida o nome:",
            styles["body"],
        )
    )
    story.append(
        XPreformatted(
            "python scripts/gerar_zip.py --membros \"Jhennyfer Joao\" --saida entrega\n"
            "# gera: entrega/Jhennyfer_Joao.Mente_Saudavel.zip\n"
            "python scripts/verificar_entrega.py\n"
            "# confere PDF, ZIP, nomes e estrutura",
            ParagraphStyle(
                "Code5",
                fontName="Courier",
                fontSize=7.6,
                leading=10.5,
                textColor=colors.HexColor("#334155"),
                backColor=colors.HexColor("#f8fafc"),
                borderColor=LINE,
                borderWidth=0.5,
                borderPadding=6,
                spaceAfter=10,
            ),
        )
    )
    story.append(
        _table(
            [
                ["Incluir no ZIP", "Excluir do ZIP"],
                [
                    "app/, database/, docs/, postman/, scripts/, tests/, .vscode/",
                    ".venv/, .git/, __pycache__/, .pytest_cache/",
                ],
                [
                    "app.py, run.py, api.http, requirements.txt, requirements-dev.txt",
                    ".env (contém senhas), *.pyc, *.zip, arquivos temporários",
                ],
                [
                    ".env.example, README.md, .gitignore",
                    "Bancos de dados locais e capturas não utilizadas",
                ],
            ],
            [8.3 * cm, 8.3 * cm],
            styles,
        )
    )

    # ------------------------ 12. Consideracoes finais --------------------
    story.append(_p("12. Considerações finais", styles["h1"]))
    story.append(
        _p(
            "O projeto aplica, de forma integrada, os conteúdos das duas disciplinas: "
            "a API Flask fornece endpoints REST com validações e respostas JSON, "
            "enquanto o PostgreSQL garante a integridade dos dados por meio de chaves, "
            "restrições, procedures, views e triggers. A separação em camadas facilita "
            "a manutenção e a evolução do sistema, e as evidências de teste comprovam "
            "o funcionamento de todas as operações exigidas.",
            styles["body"],
        )
    )

    # multiBuild monta o documento duas vezes: a primeira descobre as paginas
    # dos titulos e a segunda preenche o sumario. CanvasNumerado acrescenta
    # "Pagina X de Y" no rodape.
    doc.multiBuild(
        story,
        onFirstPage=on_page,
        onLaterPages=on_page,
        canvasmaker=CanvasNumerado,
    )


if __name__ == "__main__":
    diagram = build_diagram()
    print(f"Diagrama gerado: {diagram}")
    build_pdf()
    print(f"PDF gerado: {PDF_PATH}")
