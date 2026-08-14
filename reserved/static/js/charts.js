(() => {
    const THEME_COLOURS = {
        light: {
            grid: "#dbe4f1",
            text: "#4f6383",
            income: "#2864dc",
            reserved: "#625bdc",
            incomeFill: "rgba(40, 100, 220, 0.16)",
            reservedFill: "rgba(98, 91, 220, 0.12)",
        },
        dark: {
            grid: "#293b59",
            text: "#b5c2d8",
            income: "#82a9ff",
            reserved: "#aaa5ff",
            incomeFill: "rgba(130, 169, 255, 0.18)",
            reservedFill: "rgba(170, 165, 255, 0.14)",
        },
    };

    const activeColours = () => {
        const theme = document.documentElement.dataset.theme === "dark" ? "dark" : "light";
        return THEME_COLOURS[theme];
    };

    const drawChart = () => {
        const canvas = document.getElementById("incomeReserveChart");
        if (!canvas) return;

        const labels = JSON.parse(canvas.dataset.labels || "[]");
        const income = JSON.parse(canvas.dataset.income || "[]");
        const reserved = JSON.parse(canvas.dataset.reserved || "[]");
        const context = canvas.getContext("2d");
        const ratio = window.devicePixelRatio || 1;
        const rect = canvas.getBoundingClientRect();
        const colours = activeColours();

        canvas.width = rect.width * ratio;
        canvas.height = 330 * ratio;
        context.setTransform(ratio, 0, 0, ratio, 0, 0);

        const width = rect.width;
        const height = 330;
        const padding = { left: 52, right: 20, top: 20, bottom: 38 };
        const plotWidth = width - padding.left - padding.right;
        const plotHeight = height - padding.top - padding.bottom;
        const max = Math.max(...income, ...reserved) * 1.15 || 1;

        context.clearRect(0, 0, width, height);
        context.font = "12px Inter, system-ui, sans-serif";
        context.textAlign = "right";
        context.textBaseline = "middle";

        for (let index = 0; index <= 4; index += 1) {
            const y = padding.top + (plotHeight / 4) * index;
            const value = max - (max / 4) * index;

            context.strokeStyle = colours.grid;
            context.lineWidth = 1;
            context.beginPath();
            context.moveTo(padding.left, y);
            context.lineTo(width - padding.right, y);
            context.stroke();

            context.fillStyle = colours.text;
            context.fillText(`£${Math.round(value / 1000)}k`, padding.left - 10, y);
        }

        const xAt = (index) =>
            padding.left + (plotWidth / Math.max(1, labels.length - 1)) * index;
        const yAt = (value) =>
            padding.top + plotHeight - (value / max) * plotHeight;

        context.textAlign = "center";
        context.textBaseline = "top";

        labels.forEach((label, index) => {
            context.fillStyle = colours.text;
            context.fillText(label, xAt(index), height - padding.bottom + 12);
        });

        const drawSeries = (values, strokeColour, fillColour) => {
            const gradient = context.createLinearGradient(
                0,
                padding.top,
                0,
                height - padding.bottom,
            );
            gradient.addColorStop(0, fillColour);
            gradient.addColorStop(1, "rgba(0, 0, 0, 0)");

            context.beginPath();
            values.forEach((value, index) => {
                const x = xAt(index);
                const y = yAt(value);
                if (index === 0) context.moveTo(x, y);
                else context.lineTo(x, y);
            });

            context.strokeStyle = strokeColour;
            context.lineWidth = 3;
            context.lineJoin = "round";
            context.lineCap = "round";
            context.stroke();

            context.lineTo(xAt(values.length - 1), height - padding.bottom);
            context.lineTo(xAt(0), height - padding.bottom);
            context.closePath();
            context.fillStyle = gradient;
            context.fill();

            values.forEach((value, index) => {
                context.beginPath();
                context.arc(xAt(index), yAt(value), 4, 0, Math.PI * 2);
                context.fillStyle = strokeColour;
                context.fill();

                context.beginPath();
                context.arc(xAt(index), yAt(value), 7, 0, Math.PI * 2);
                context.strokeStyle = "rgba(255, 255, 255, 0.55)";
                context.lineWidth = 2;
                context.stroke();
            });
        };

        drawSeries(income, colours.income, colours.incomeFill);
        drawSeries(reserved, colours.reserved, colours.reservedFill);
    };

    let resizeTimer;
    window.addEventListener("resize", () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(drawChart, 100);
    });

    window.addEventListener("reserved-theme-change", drawChart);
    window.addEventListener("DOMContentLoaded", drawChart);
})();
