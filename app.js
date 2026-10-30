
const API = "/api/properties";

const el = id => document.getElementById(id);

const grid = el("grid");
const search = el("search");
const type = el("type");
const sort = el("sort");
const dialog = el("details");

let properties = [];
let favorites = new Set();

try {
    favorites = new Set(
        JSON.parse(localStorage.getItem("skyline-favorites") || "[]")
    );
} catch {
    favorites = new Set();
}

const money = value =>
    new Intl.NumberFormat("uk-UA").format(value) + " ₴";

const typeNames = {
    apartment: "Квартира",
    studio: "Студія",
    house: "Будинок"
};

let toastTimeout;

function notify(message) {
    const toast = el("toast");

    toast.textContent = message;
    toast.classList.add("visible");

    clearTimeout(toastTimeout);

    toastTimeout = setTimeout(() => {
        toast.classList.remove("visible");
    }, 2800);
}

function node(tag, className, text) {
    const element = document.createElement(tag);

    if (className) {
        element.className = className;
    }

    if (text !== undefined) {
        element.textContent = text;
    }

    return element;
}

function propertyCard(item, index) {
    const card = node("article", "property-card");
    const media = node("div", "property-media");
    const image = node("img");

    image.src = item.image || "";
    image.alt = "Інтер’єр: " + item.title;
    image.loading = index < 3 ? "eager" : "lazy";

    image.onerror = () => {
        image.style.display = "none";
        media.classList.add("no-photo");
    };

    media.append(image);

    media.append(
        node(
            "span",
            "type-pill",
            typeNames[item.type] || "Нерухомість"
        )
    );

    const favorite = node(
        "button",
        "favorite" + (favorites.has(item.id) ? " selected" : ""),
        favorites.has(item.id) ? "♥" : "♡"
    );

    favorite.type = "button";

    favorite.setAttribute(
        "aria-label",
        "Додати або прибрати з обраного"
    );

    favorite.addEventListener("click", event => {
        event.stopPropagation();

        if (favorites.has(item.id)) {
            favorites.delete(item.id);
        } else {
            favorites.add(item.id);
        }

        localStorage.setItem(
            "skyline-favorites",
            JSON.stringify([...favorites])
        );

        favorite.classList.toggle(
            "selected",
            favorites.has(item.id)
        );

        favorite.textContent = favorites.has(item.id) ? "♥" : "♡";

        notify(
            favorites.has(item.id)
                ? "Додано до обраного"
                : "Прибрано з обраного"
        );
    });

    media.append(favorite);
    card.append(media);

    const body = node("div", "property-body");

    body.append(
        node("div", "property-price", money(item.price))
    );

    body.append(
        node("h3", "property-name", item.title)
    );

    body.append(
        node(
            "p",
            "property-location",
            "⌖  " + item.city +
            (item.district ? ", " + item.district : "")
        )
    );

    const bottom = node("div", "property-bottom");

    bottom.append(
        node("span", "", "▦ " + item.rooms + " кімн.")
    );

    bottom.append(
        node("span", "", "□ " + item.area + " м²")
    );

    bottom.append(
        node("span", "", "↑ " + item.floor + " поверх")
    );

    body.append(bottom);

    const view = node(
        "button",
        "view-property",
        "Детальніше ↗"
    );

    view.type = "button";

    view.addEventListener("click", () => {
        openDetails(item);
    });

    body.append(view);
    card.append(body);

    return card;
}

function openDetails(item) {
    const content = el("detailsContent");

    content.replaceChildren();

    const img = node("img", "detail-image");

    img.src = item.image || "";
    img.alt = "Інтер’єр: " + item.title;

    content.append(img);

    const inner = node("div", "detail-inner");

    inner.append(
        node(
            "span",
            "eyebrow dark",
            typeNames[item.type] || "Нерухомість"
        )
    );

    inner.append(
        node("h2", "", item.title)
    );

    inner.append(
        node(
            "p",
            "detail-place",
            item.city +
            (item.district ? " · " + item.district : "")
        )
    );

    inner.append(
        node("strong", "detail-price", money(item.price))
    );

    inner.append(
        node(
            "p",
            "",
            item.description || "Деталі об’єкта уточнюються."
        )
    );

    inner.append(
        node(
            "p",
            "detail-place",
            `${item.rooms} кімн. · ${item.area} м² · ${item.floor} поверх`
        )
    );

    const note = node(
        "p",
        "demo-warning",
        "Демонстраційний об’єкт. Не є реальною пропозицією продажу."
    );

    inner.append(note);
    content.append(inner);

    dialog.showModal();
}

async function loadProperties() {
    grid.replaceChildren(
        node("p", "message", "Завантаження каталогу…")
    );

    const params = new URLSearchParams({
        search: search.value.trim(),
        type: type.value,
        sort: sort.value
    });

    try {
        const response = await fetch(`${API}?${params}`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        properties = await response.json();

        render();
    } catch (error) {
        grid.replaceChildren(
            node(
                "p",
                "message",
                "Не вдалося завантажити об’єкти. Перевірте, чи запущено FastAPI."
            )
        );

        el("resultCount").textContent = "Помилка завантаження";
    }
}

function render() {
    grid.replaceChildren();

    el("resultCount").textContent =
        `Знайдено ${properties.length} ` +
        (properties.length === 1 ? "об’єкт" : "об’єктів");

    if (!properties.length) {
        grid.append(
            node(
                "p",
                "message",
                "Нічого не знайдено. Спробуйте змінити фільтри."
            )
        );

        return;
    }

    properties.forEach((item, index) => {
        grid.append(propertyCard(item, index));
    });
}

let searchTimer;

search.addEventListener("input", () => {
    clearTimeout(searchTimer);

    searchTimer = setTimeout(loadProperties, 250);
});

type.addEventListener("change", loadProperties);

sort.addEventListener("change", loadProperties);

el("reset").addEventListener("click", () => {
    search.value = "";
    type.value = "all";
    sort.value = "featured";

    loadProperties();
});

el("closeDetails").addEventListener("click", () => {
    dialog.close();
});

dialog.addEventListener("click", event => {
    if (event.target === dialog) {
        dialog.close();
    }
});

el("menuToggle").addEventListener("click", () => {
    const open = document
        .querySelector(".nav-links")
        .classList.toggle("open");

    el("menuToggle").setAttribute(
        "aria-expanded",
        String(open)
    );
});

document.querySelectorAll(".nav-links a").forEach(link => {
    link.addEventListener("click", () => {
        document
            .querySelector(".nav-links")
            .classList.remove("open");

        el("menuToggle").setAttribute(
            "aria-expanded",
            "false"
        );
    });
});

loadProperties();
