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


def build_pdf():
    styles = _styles()
    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=A4,
        leftMargin=2.1 * cm,
        rightMargin=2.1 * cm,
        topMargin=2.0 * cm,
        bottomMargin=1.8 * cm,
        title="Documentacao - Mente Saudavel",
        author="Equipe Mente Saudavel - IFRO",
        subject="Projeto integrador de Desenvolvimento Web III e Banco de Dados II",
    )

    def on_page(canvas, document):
        canvas.saveState()
        if document.page > 1:
            canvas.setFont("Arial", 7.5)
            canvas.setFillColor(GRAY)
            canvas.drawString(2.1 * cm, A4[1] - 1.35 * cm, "Mente Saudavel — Documentacao do sistema")
            canvas.drawRightString(A4[0] - 2.1 * cm, A4[1] - 1.35 * cm, "IFRO · 2026")
            canvas.setStrokeColor(LINE)
            canvas.setLineWidth(0.6)
            canvas.line(2.1 * cm, A4[1] - 1.55 * cm, A4[0] - 2.1 * cm, A4[1] - 1.55 * cm)
        canvas.setFont("Arial", 8)
        canvas.setFillColor(GRAY)
        canvas.drawCentredString(A4[0] / 2, 1.1 * cm, f"Pagina {document.page}")
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
        _p("Equipe", styles["cell_bold"]),
        Spacer(1, 0.25 * cm),
        _p("Integrante 1: ______________________________________", styles["small"]),
        Spacer(1, 0.35 * cm),
        _p("Integrante 2: ______________________________________", styles["small"]),
        Spacer(1, 0.35 * cm),
        _p("Integrante 3: ______________________________________", styles["small"]),
        Spacer(1, 0.35 * cm),
        _p("Integrante 4: ______________________________________", styles["small"]),
        Spacer(1, 0.9 * cm),
        _p(
            "Substitua os nomes acima pelos integrantes da equipe antes da entrega.",
            styles["caption"],
        ),
        PageBreak(),
    ]

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
            "Foram implementadas mais de 20 check constraints, entre elas: "
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

    story.append(_p("5.3 Comentários das colunas no script do banco", styles["h2"]))
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

    # ----------------------------- 8. Testes ------------------------------
    story.append(PageBreak())
    story.append(_p("8. Testes e evidências", styles["h1"]))
    story.append(
        _p(
            "Os testes foram executados no painel web, em uma página de evidências "
            "que dispara requisições reais contra a API e na suíte automatizada "
            "(pytest). A coleção do Postman também acompanha o repositório.",
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
    story += _image_block(
        IMG_DIR / "testes-api.png",
        "Figura 5 — Execução real dos endpoints: health check, cadastro via stored procedure, "
        "listagem, agendamento, resumo e relatório.",
        styles,
        max_width=13.2 * cm,
        max_height=19.5 * cm,
    )

    story.append(PageBreak())
    story += _image_block(
        IMG_DIR / "api-pacientes.png",
        "Figura 6 — Resposta JSON da listagem paginada de pacientes.",
        styles,
        max_width=16.0 * cm,
        max_height=9.0 * cm,
    )
    story.append(
        _p(
            "Suíte automatizada: <font name='Courier'>pytest -q</font> — 23 testes "
            "aprovados, cobrindo validações de CPF, e-mail, datas, paginação e o fluxo "
            "completo de cadastro, consulta, evolução e relatório.",
            styles["body"],
        )
    )

    # -------------------------- 9. Divisao de tarefas ----------------------
    story.append(_p("9. Divisão de tarefas", styles["h1"]))
    story.append(
        _p(
            "Cada entrega deve ser revisada por pelo menos outro integrante (duplo "
            "check), conforme orientação da atividade.",
            styles["body"],
        )
    )
    story.append(
        _table(
            [
                ["Integrante", "Desenvolvimento", "Documentação", "Revisão"],
                ["(preencher)", "Banco de dados, procedures e views", "Script SQL comentado", "(outro integrante)"],
                ["(preencher)", "API Flask e validações", "Endpoints e testes", "(outro integrante)"],
                ["(preencher)", "Frontend e integração", "Capturas de tela", "(outro integrante)"],
                ["(preencher)", "Testes e relatórios", "Documento final", "(outro integrante)"],
            ],
            [3.1 * cm, 5.2 * cm, 4.4 * cm, 3.9 * cm],
            styles,
        )
    )
    story.append(Spacer(1, 0.3 * cm))

    # ---------------------------- 10. Execucao ----------------------------
    story.append(_p("10. Como executar", styles["h1"]))
    story.append(
        _bullets(
            [
                "Criar o banco e executar os scripts na ordem 00, 01, 02, 03 e 04 da pasta <font name='Courier'>database/</font>.",
                "Copiar <font name='Courier'>.env.example</font> para <font name='Courier'>.env</font> e configurar usuário e senha do PostgreSQL.",
                "Criar o ambiente virtual e instalar as dependências de <font name='Courier'>requirements.txt</font>.",
                "Executar <font name='Courier'>python run.py</font> e acessar <font name='Courier'>http://localhost:5000</font>.",
            ],
            styles,
        )
    )
    story.append(
        _p(
            "As instruções completas, incluindo testes e Postman, estão no "
            "<font name='Courier'>README.md</font> do repositório.",
            styles["body"],
        )
    )

    # ------------------------ 11. Consideracoes finais --------------------
    story.append(_p("11. Considerações finais", styles["h1"]))
    story.append(
        _p(
            "O projeto aplica, de forma integrada, os conteúdos das duas disciplinas: "
            "a API Flask fornece endpoints REST com validações e respostas JSON, "
            "enquanto o PostgreSQL garante a integridade dos dados por meio de chaves, "
            "restrições, procedures, views e triggers. A separação em camadas facilita "
            "a manutenção e a evolução do sistema.",
            styles["body"],
        )
    )

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)


if __name__ == "__main__":
    diagram = build_diagram()
    print(f"Diagrama gerado: {diagram}")
    build_pdf()
    print(f"PDF gerado: {PDF_PATH}")
