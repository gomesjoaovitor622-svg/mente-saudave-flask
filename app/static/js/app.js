/* ==========================================================================
   Mente Saudavel - consumo da API (fetch + renderizacao)
   ========================================================================== */

const API = "/api";

const state = {
    pacientes: [],
    psicologos: [],
    consultas: [],
    resumo: null,
    view: "dashboard",
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

const TITLES = {
    dashboard: ["Painel geral", "Visao rapida da clinica e dos atendimentos."],
    pacientes: ["Pacientes", "Cadastro, edicao e remocao de pacientes."],
    agenda: ["Agenda", "Agendamento e acompanhamento das consultas."],
    psicologos: ["Psicologos", "Profissionais que atendem na clinica."],
};

/* ------------------------------- Utilidades ------------------------------ */

function esc(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function formatDateTime(iso) {
    if (!iso) return "-";
    return new Date(iso).toLocaleString("pt-BR", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    });
}

function formatDate(iso) {
    if (!iso) return "-";
    return new Date(`${iso}T00:00:00`).toLocaleDateString("pt-BR");
}

function formatMoney(value) {
    return Number(value ?? 0).toLocaleString("pt-BR", {
        style: "currency",
        currency: "BRL",
    });
}

function formatCpf(cpf) {
    const digits = String(cpf ?? "").replace(/\D/g, "");
    if (digits.length !== 11) return cpf ?? "-";
    return `${digits.slice(0, 3)}.${digits.slice(3, 6)}.${digits.slice(6, 9)}-${digits.slice(9)}`;
}

function toLocalInput(iso) {
    if (!iso) return "";
    const date = new Date(iso);
    const pad = (n) => String(n).padStart(2, "0");
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function showToast(message, type = "success") {
    const toast = $("#toast");
    toast.textContent = message;
    toast.className = `toast show ${type === "error" ? "error" : ""}`;
    clearTimeout(showToast.timer);
    showToast.timer = setTimeout(() => {
        toast.className = "toast";
    }, 3600);
}

async function api(path, options = {}) {
    const response = await fetch(`${API}${path}`, {
        headers: { "Content-Type": "application/json", ...(options.headers || {}) },
        ...options,
    });

    const text = await response.text();
    const body = text ? JSON.parse(text) : {};

    if (!response.ok) {
        const message = body.mensagem || `Erro ${response.status}`;
        throw new Error(message);
    }
    return body;
}

/* --------------------------------- Navegacao ----------------------------- */

function switchView(view) {
    if (!TITLES[view]) view = "dashboard";
    state.view = view;
    if (window.location.hash !== `#${view}`) {
        window.history.replaceState(null, "", `#${view}`);
    }

    $$(".nav-item").forEach((item) => {
        item.classList.toggle("active", item.dataset.view === view);
    });
    $$(".view").forEach((section) => {
        section.classList.toggle("active", section.id === `view-${view}`);
    });

    const [title, subtitle] = TITLES[view];
    $("#page-title").textContent = title;
    $("#page-subtitle").textContent = subtitle;

    if (view === "dashboard") loadDashboard();
    if (view === "pacientes") loadPacientes();
    if (view === "agenda") loadConsultas();
    if (view === "psicologos") loadPsicologos();
}

/* ---------------------------------- Painel -------------------------------- */

async function loadDashboard() {
    try {
        const [resumo, consultas] = await Promise.all([
            api("/relatorios/resumo"),
            api("/consultas?per_page=100"),
        ]);

        state.resumo = resumo;
        $("#stat-pacientes").textContent = resumo.totais.pacientes_ativos;
        $("#stat-psicologos").textContent = resumo.totais.psicologos_ativos;
        $("#stat-agendadas").textContent = resumo.totais.consultas_agendadas;
        $("#stat-humor").textContent = Number(resumo.totais.humor_medio).toFixed(1);

        const proximas = consultas.dados
            .filter((c) => c.status === "agendada")
            .sort((a, b) => new Date(a.data_hora) - new Date(b.data_hora))
            .slice(0, 5);

        const container = $("#proximas-consultas");
        container.innerHTML = proximas.length
            ? proximas
                  .map(
                      (c) => `
                <div class="list-row">
                    <div>
                        <div class="who">${esc(c.paciente)}</div>
                        <div class="pro">${esc(c.psicologo)} &middot; ${esc(c.modalidade)}</div>
                    </div>
                    <div class="when">${formatDateTime(c.data_hora)}</div>
                </div>`
                  )
                  .join("")
            : '<p class="empty">Nenhuma consulta agendada.</p>';

        const especialidades = resumo.consultas_por_especialidade;
        const maior = Math.max(...especialidades.map((e) => Number(e.total_consultas)), 1);

        $("#especialidades").innerHTML = especialidades.length
            ? especialidades
                  .map(
                      (item) => `
                <div class="bar-row">
                    <div class="bar-label">
                        <span>${esc(item.especialidade)}</span>
                        <strong>${item.total_consultas}</strong>
                    </div>
                    <div class="bar-track">
                        <div class="bar-fill" style="width: ${(Number(item.total_consultas) / maior) * 100}%"></div>
                    </div>
                </div>`
                  )
                  .join("")
            : '<p class="empty">Sem dados de consultas.</p>';
    } catch (error) {
        showToast(error.message, "error");
    }
}

/* --------------------------------- Pacientes ------------------------------ */

async function loadPacientes() {
    const nome = $("#busca-paciente").value.trim();
    const status = $("#filtro-status-paciente").value;
    const params = new URLSearchParams({ per_page: "100" });
    if (nome) params.set("nome", nome);
    if (status) params.set("status", status);

    try {
        const response = await api(`/pacientes?${params}`);
        state.pacientes = response.dados;
        renderPacientes();
    } catch (error) {
        showToast(error.message, "error");
    }
}

function renderPacientes() {
    const tbody = $("#tabela-pacientes");

    if (!state.pacientes.length) {
        tbody.innerHTML = '<tr><td colspan="5" class="empty">Nenhum paciente encontrado.</td></tr>';
        return;
    }

    tbody.innerHTML = state.pacientes
        .map(
            (p) => `
        <tr>
            <td>
                <span class="cell-strong">${esc(p.nome)}</span>
                <span class="cell-sub">${formatCpf(p.cpf)} &middot; ${formatDate(p.data_nascimento)}</span>
            </td>
            <td>
                ${esc(p.email)}
                <span class="cell-sub">${esc(p.telefone || "Sem telefone")}</span>
            </td>
            <td>${esc(p.cidade || "-")}</td>
            <td><span class="badge-pill badge-${esc(p.status)}">${esc(p.status)}</span></td>
            <td>
                <div class="actions">
                    <button class="btn btn-ghost btn-sm" data-edit-patient="${p.id_paciente}">Editar</button>
                    <button class="btn btn-danger btn-sm" data-delete-patient="${p.id_paciente}">Excluir</button>
                </div>
            </td>
        </tr>`
        )
        .join("");
}

function openPatientModal(paciente = null) {
    const form = $("#form-paciente");
    form.reset();
    form.id_paciente.value = paciente?.id_paciente ?? "";
    $("#titulo-modal-paciente").textContent = paciente ? "Editar paciente" : "Novo paciente";
    $(".status-field", form).classList.toggle("visible", Boolean(paciente));

    if (paciente) {
        form.nome.value = paciente.nome;
        form.cpf.value = formatCpf(paciente.cpf);
        form.email.value = paciente.email;
        form.telefone.value = paciente.telefone ?? "";
        form.data_nascimento.value = paciente.data_nascimento ?? "";
        form.genero.value = paciente.genero ?? "nao_informado";
        form.cidade.value = paciente.cidade ?? "";
        form.observacoes.value = paciente.observacoes ?? "";
        form.status.value = paciente.status;
    }

    openModal("modal-paciente");
}

async function submitPatient(event) {
    event.preventDefault();
    const form = event.target;
    const id = form.id_paciente.value;
    const cpfDigits = form.cpf.value.replace(/\D/g, "");

    if (cpfDigits.length !== 11) {
        showToast("Informe um CPF com 11 digitos.", "error");
        return;
    }

    const payload = {
        nome: form.nome.value.trim(),
        cpf: cpfDigits,
        email: form.email.value.trim(),
        data_nascimento: form.data_nascimento.value,
        telefone: form.telefone.value.trim() || null,
        genero: form.genero.value,
        cidade: form.cidade.value.trim() || null,
        observacoes: form.observacoes.value.trim() || null,
    };
    if (id) payload.status = form.status.value;

    try {
        if (id) {
            await api(`/pacientes/${id}`, { method: "PUT", body: JSON.stringify(payload) });
            showToast("Paciente atualizado com sucesso.");
        } else {
            await api("/pacientes", { method: "POST", body: JSON.stringify(payload) });
            showToast("Paciente cadastrado com sucesso.");
        }
        closeModal("modal-paciente");
        await loadPacientes();
        if (state.view === "dashboard") loadDashboard();
    } catch (error) {
        showToast(error.message, "error");
    }
}

async function deletePatient(id) {
    if (!window.confirm("Deseja realmente excluir este paciente? As consultas vinculadas tambem serao removidas.")) {
        return;
    }
    try {
        await api(`/pacientes/${id}`, { method: "DELETE" });
        showToast("Paciente removido.");
        await loadPacientes();
        if (state.view === "dashboard") loadDashboard();
    } catch (error) {
        showToast(error.message, "error");
    }
}

/* ---------------------------------- Agenda -------------------------------- */

async function loadConsultas() {
    const status = $("#filtro-status-consulta").value;
    const params = new URLSearchParams({ per_page: "100" });
    if (status) params.set("status", status);

    try {
        const response = await api(`/consultas?${params}`);
        state.consultas = response.dados;
        renderConsultas();
    } catch (error) {
        showToast(error.message, "error");
    }
}

function renderConsultas() {
    const tbody = $("#tabela-consultas");

    if (!state.consultas.length) {
        tbody.innerHTML = '<tr><td colspan="7" class="empty">Nenhuma consulta encontrada.</td></tr>';
        return;
    }

    tbody.innerHTML = state.consultas
        .map(
            (c) => `
        <tr>
            <td>
                <span class="cell-strong">${formatDateTime(c.data_hora)}</span>
                <span class="cell-sub">${c.duracao_minutos} minutos</span>
            </td>
            <td>${esc(c.paciente)}</td>
            <td>
                ${esc(c.psicologo)}
                <span class="cell-sub">${esc(c.especialidade)}</span>
            </td>
            <td><span class="badge-pill badge-${esc(c.modalidade)}">${esc(c.modalidade)}</span></td>
            <td>${formatMoney(c.valor)}</td>
            <td><span class="badge-pill badge-${esc(c.status)}">${esc(c.status)}</span></td>
            <td>
                <div class="actions">
                    <button class="btn btn-ghost btn-sm" data-edit-consulta="${c.id_consulta}">Editar</button>
                    <button class="btn btn-danger btn-sm" data-delete-consulta="${c.id_consulta}">Excluir</button>
                </div>
            </td>
        </tr>`
        )
        .join("");
}

function fillSelects() {
    const patientSelect = $('#form-consulta select[name="id_paciente"]');
    const psychologistSelect = $('#form-consulta select[name="id_psicologo"]');

    patientSelect.innerHTML =
        '<option value="">Selecione...</option>' +
        state.pacientes
            .filter((p) => p.status === "ativo")
            .map((p) => `<option value="${p.id_paciente}">${esc(p.nome)}</option>`)
            .join("");

    psychologistSelect.innerHTML =
        '<option value="">Selecione...</option>' +
        state.psicologos
            .filter((p) => p.ativo)
            .map((p) => `<option value="${p.id_psicologo}">${esc(p.nome)} - ${esc(p.especialidade)}</option>`)
            .join("");
}

async function openConsultationModal(consulta = null) {
    try {
        const [pacientes, psicologos] = await Promise.all([
            api("/pacientes?per_page=100"),
            api("/psicologos?per_page=100"),
        ]);
        state.pacientes = pacientes.dados;
        state.psicologos = psicologos.dados;
    } catch (error) {
        showToast(error.message, "error");
        return;
    }

    const form = $("#form-consulta");
    form.reset();
    fillSelects();

    form.id_consulta.value = consulta?.id_consulta ?? "";
    $("#titulo-modal-consulta").textContent = consulta ? "Editar consulta" : "Nova consulta";
    $(".status-field", form).classList.toggle("visible", Boolean(consulta));

    if (consulta) {
        form.id_paciente.value = consulta.id_paciente;
        form.id_psicologo.value = consulta.id_psicologo;
        form.data_hora.value = toLocalInput(consulta.data_hora);
        form.duracao_minutos.value = consulta.duracao_minutos;
        form.modalidade.value = consulta.modalidade;
        form.valor.value = consulta.valor ?? "";
        form.observacoes.value = consulta.observacoes ?? "";
        form.status.value = consulta.status;
    } else {
        form.duracao_minutos.value = 50;
    }

    openModal("modal-consulta");
}

async function submitConsultation(event) {
    event.preventDefault();
    const form = event.target;
    const id = form.id_consulta.value;

    const payload = {
        id_paciente: Number(form.id_paciente.value),
        id_psicologo: Number(form.id_psicologo.value),
        data_hora: form.data_hora.value,
        duracao_minutos: Number(form.duracao_minutos.value || 50),
        modalidade: form.modalidade.value,
        observacoes: form.observacoes.value.trim() || null,
    };
    if (form.valor.value) payload.valor = Number(form.valor.value);
    if (id) payload.status = form.status.value;

    try {
        if (id) {
            await api(`/consultas/${id}`, { method: "PUT", body: JSON.stringify(payload) });
            showToast("Consulta atualizada com sucesso.");
        } else {
            await api("/consultas", { method: "POST", body: JSON.stringify(payload) });
            showToast("Consulta agendada com sucesso.");
        }
        closeModal("modal-consulta");
        await loadConsultas();
        if (state.view === "dashboard") loadDashboard();
    } catch (error) {
        showToast(error.message, "error");
    }
}

async function deleteConsultation(id) {
    if (!window.confirm("Deseja realmente excluir esta consulta?")) return;
    try {
        await api(`/consultas/${id}`, { method: "DELETE" });
        showToast("Consulta removida.");
        await loadConsultas();
        if (state.view === "dashboard") loadDashboard();
    } catch (error) {
        showToast(error.message, "error");
    }
}

/* -------------------------------- Psicologos ------------------------------ */

async function loadPsicologos() {
    try {
        const response = await api("/psicologos?per_page=100");
        state.psicologos = response.dados;
        renderPsicologos();
    } catch (error) {
        showToast(error.message, "error");
    }
}

function renderPsicologos() {
    const tbody = $("#tabela-psicologos");

    if (!state.psicologos.length) {
        tbody.innerHTML = '<tr><td colspan="6" class="empty">Nenhum psicologo cadastrado.</td></tr>';
        return;
    }

    tbody.innerHTML = state.psicologos
        .map(
            (p) => `
        <tr>
            <td>
                <span class="cell-strong">${esc(p.nome)}</span>
                <span class="cell-sub">${esc(p.email)}</span>
            </td>
            <td>${esc(p.crp)}</td>
            <td>${esc(p.especialidade)}</td>
            <td>${formatMoney(p.valor_sessao)}</td>
            <td><span class="badge-pill badge-${p.ativo ? "ativo" : "inativo"}">${p.ativo ? "ativo" : "inativo"}</span></td>
            <td>
                <div class="actions">
                    <button class="btn btn-ghost btn-sm" data-edit-psychologist="${p.id_psicologo}">Editar</button>
                    <button class="btn btn-danger btn-sm" data-delete-psychologist="${p.id_psicologo}">Excluir</button>
                </div>
            </td>
        </tr>`
        )
        .join("");
}

function openPsychologistModal(psicologo = null) {
    const form = $("#form-psicologo");
    form.reset();
    form.id_psicologo.value = psicologo?.id_psicologo ?? "";
    $("#titulo-modal-psicologo").textContent = psicologo ? "Editar psicologo" : "Novo psicologo";

    if (psicologo) {
        form.nome.value = psicologo.nome;
        form.crp.value = psicologo.crp;
        form.email.value = psicologo.email;
        form.especialidade.value = psicologo.especialidade;
        form.valor_sessao.value = psicologo.valor_sessao;
        form.ativo.value = String(psicologo.ativo);
    }

    openModal("modal-psicologo");
}

async function submitPsychologist(event) {
    event.preventDefault();
    const form = event.target;
    const id = form.id_psicologo.value;

    const payload = {
        nome: form.nome.value.trim(),
        crp: form.crp.value.trim(),
        email: form.email.value.trim(),
        especialidade: form.especialidade.value.trim(),
        valor_sessao: Number(form.valor_sessao.value),
        ativo: form.ativo.value === "true",
    };

    try {
        if (id) {
            await api(`/psicologos/${id}`, { method: "PUT", body: JSON.stringify(payload) });
            showToast("Psicologo atualizado com sucesso.");
        } else {
            await api("/psicologos", { method: "POST", body: JSON.stringify(payload) });
            showToast("Psicologo cadastrado com sucesso.");
        }
        closeModal("modal-psicologo");
        await loadPsicologos();
        if (state.view === "dashboard") loadDashboard();
    } catch (error) {
        showToast(error.message, "error");
    }
}

async function deletePsychologist(id) {
    if (!window.confirm("Deseja realmente excluir este psicologo?")) return;
    try {
        await api(`/psicologos/${id}`, { method: "DELETE" });
        showToast("Psicologo removido.");
        await loadPsicologos();
        if (state.view === "dashboard") loadDashboard();
    } catch (error) {
        showToast(error.message, "error");
    }
}

/* ---------------------------------- Modais -------------------------------- */

function openModal(id) {
    const modal = document.getElementById(id);
    modal.classList.add("open");
    modal.setAttribute("aria-hidden", "false");
}

function closeModal(id) {
    const modal = document.getElementById(id);
    modal.classList.remove("open");
    modal.setAttribute("aria-hidden", "true");
}

/* --------------------------------- Eventos -------------------------------- */

function bindEvents() {
    $$(".nav-item").forEach((item) => {
        item.addEventListener("click", () => switchView(item.dataset.view));
    });

    $$("[data-goto]").forEach((button) => {
        button.addEventListener("click", () => switchView(button.dataset.goto));
    });

    $$("[data-close]").forEach((button) => {
        button.addEventListener("click", () => closeModal(button.dataset.close));
    });

    $$(".modal").forEach((modal) => {
        modal.addEventListener("click", (event) => {
            if (event.target === modal) closeModal(modal.id);
        });
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            $$(".modal.open").forEach((modal) => closeModal(modal.id));
        }
    });

    $("#refresh-btn").addEventListener("click", () => switchView(state.view));

    $("#novo-paciente").addEventListener("click", () => openPatientModal());
    $("#form-paciente").addEventListener("submit", submitPatient);

    $("#nova-consulta").addEventListener("click", () => openConsultationModal());
    $("#form-consulta").addEventListener("submit", submitConsultation);

    $("#novo-psicologo").addEventListener("click", () => openPsychologistModal());
    $("#form-psicologo").addEventListener("submit", submitPsychologist);

    let searchTimer;
    $("#busca-paciente").addEventListener("input", () => {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(loadPacientes, 300);
    });
    $("#filtro-status-paciente").addEventListener("change", loadPacientes);
    $("#filtro-status-consulta").addEventListener("change", loadConsultas);

    $("#tabela-pacientes").addEventListener("click", (event) => {
        const editId = event.target.dataset.editPatient;
        const deleteId = event.target.dataset.deletePatient;
        if (editId) {
            const paciente = state.pacientes.find((p) => p.id_paciente === Number(editId));
            if (paciente) openPatientModal(paciente);
        }
        if (deleteId) deletePatient(deleteId);
    });

    $("#tabela-consultas").addEventListener("click", (event) => {
        const editId = event.target.dataset.editConsulta;
        const deleteId = event.target.dataset.deleteConsulta;
        if (editId) {
            const consulta = state.consultas.find((c) => c.id_consulta === Number(editId));
            if (consulta) openConsultationModal(consulta);
        }
        if (deleteId) deleteConsultation(deleteId);
    });

    $("#tabela-psicologos").addEventListener("click", (event) => {
        const editId = event.target.dataset.editPsychologist;
        const deleteId = event.target.dataset.deletePsychologist;
        if (editId) {
            const psicologo = state.psicologos.find((p) => p.id_psicologo === Number(editId));
            if (psicologo) openPsychologistModal(psicologo);
        }
        if (deleteId) deletePsychologist(deleteId);
    });
}

document.addEventListener("DOMContentLoaded", () => {
    bindEvents();
    const initialView = window.location.hash.replace("#", "");
    switchView(TITLES[initialView] ? initialView : "dashboard");
});
