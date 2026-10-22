// variables
let fairOdds = 0;
let oddsInitialized = false;

// websockets
const wsUrl = `ws://${window.location.host}/ws`;
const ws = new WebSocket(wsUrl);

// dom elements
const oddsInput = document.getElementById("oddsInput");
const amountInput = document.getElementById("amountInput");
const backRadio = document.getElementById("backRadio");
const liabilitySpan = document.getElementById("liabilitySpan");

const betForm = document.getElementById('betForm');

const ctx = document.getElementById('liveChart');

// theme (read from the CSS variables in style.css)
const css = getComputedStyle(document.documentElement);
const cssVar = name => css.getPropertyValue(name).trim();
const alpha = (hex, a) => {
    const n = parseInt(hex.slice(1), 16);
    return `rgba(${n >> 16}, ${(n >> 8) & 255}, ${n & 255}, ${a})`;
};

const theme = {
    text: cssVar('--text'),
    muted: cssVar('--muted'),
    grid: alpha(cssVar('--text'), 0.06),
    surface: cssVar('--surface'),
    border: cssVar('--border'),
    lay: alpha(cssVar('--lay'), 0.75),
    back: alpha(cssVar('--back'), 0.75),
    matched: alpha(cssVar('--accent'), 0.6),
    fairLine: alpha(cssVar('--text'), 0.5),
};

// fair odds line
const fairLine = {
    id: 'fairLine',
    afterDatasetsDraw(chart) {
        const n = chart.data.labels.length;
        if (n < 3) return;
        const idx = (n - 1) / 2;

        const { ctx, chartArea: { top, bottom }, scales: { x } } = chart;
        const px = x.getPixelForValue(idx);

        ctx.save();
        ctx.setLineDash([6, 4]);
        ctx.strokeStyle = theme.fairLine;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(px, top);
        ctx.lineTo(px, bottom);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.restore();
    }
}

// chart initialization
Chart.defaults.color = theme.muted;
Chart.defaults.font.family = cssVar('--pico-font-family');
Chart.defaults.font.size = 11;

const chart = new Chart(ctx, {
type: 'line',
data: {
    labels: [],
    datasets: [
    {
        label: 'lay',
        data: [],
        stepped: 'middle',
        fill: 'origin',
        borderColor: 'transparent',
        backgroundColor: theme.lay,
        borderWidth: 1.5,
        pointRadius: 0,
    },
    {
        label: 'back',
        data: [],
        stepped: 'middle',
        fill: 'origin',
        borderColor: 'transparent',
        backgroundColor: theme.back,
        borderWidth: 1.5,
        pointRadius: 0,
    },
    {
        label: 'matched',
        data: [],
        stepped: 'middle',
        fill: 'origin',
        borderColor: 'transparent',
        backgroundColor: theme.matched,
        borderWidth: 1.5,
        pointRadius: 0,
    },
    ],
},
options: {
    responsive: true,
    maintainAspectRatio: false,
    layout: { padding: { top: 20 } },
    interaction: { mode: 'index', intersect: false },
    animation: {
        duration: 100
    },
    scales: {
    x: { title: { display: true, text: 'lay ◀ odds ▶ back', color: theme.muted, font: { size: 11, weight: 500 } },
        grid: { color: theme.grid },
        ticks: { color: theme.muted },
        border: {display: false },
        display: true,
    },
    y: {
        afterDataLimits: (scale) => {
            const maxLimit = Math.max(Math.abs(scale.max), Math.abs(scale.min));
            scale.max = maxLimit;
            scale.min = -maxLimit;
        },
        title: { display: true, text: 'liquidity', color: theme.muted, font: { size: 11, weight: 500 } },
        ticks: { callback: v => Math.abs(v).toLocaleString(), color: theme.muted },
        grid: { color: theme.grid },
        border: { display: false },
    },
    },
    plugins: {
        legend: {
            labels: { color: theme.muted, usePointStyle: true, pointStyle: 'rectRounded', boxWidth: 8, boxHeight: 8 },
        },
        tooltip: {
            backgroundColor: theme.surface,
            borderColor: theme.border,
            borderWidth: 1,
            cornerRadius: 8,
            padding: 10,
            titleColor: theme.muted,
            bodyColor: theme.text,
            boxPadding: 4,
            callbacks: {
                label: c => `${c.dataset.label}: ${Math.abs(c.parsed.y).toLocaleString()}`,
            },
        },
    },
},
plugins: [fairLine]
});

function _getLiabilityValue (odds, stake) {
    if (isNaN(odds) || isNaN(stake)) return 0;
    if (odds < 1) return 0;

    let l = 0;

    if (!backRadio.checked) {
        l = (odds - 1) * stake;
    }
    else {
        l = stake;
    }

    return l;
}

function updateLiability () {
    let odds = parseFloat(oddsInput.value);
    let stake = parseFloat(amountInput.value);
    let l = _getLiabilityValue(odds, stake);
    
    liabilitySpan.textContent = l.toFixed(2);
}

function onBetTypeChanged() {
    oddsInitialized = false;
}

betForm.addEventListener('submit', async (event) => {
  event.preventDefault();

  const isBack = document.getElementById('backRadio').checked;
  const betAmount = parseFloat(document.getElementById('amountInput').value);
  const betOdds = parseFloat(document.getElementById('oddsInput').value);

  // Convert floats to integer ticks before sending
  const payload = {
    is_back: isBack,
    bet_amount: Math.round(betAmount * 100),
    bet_odds: Math.round(betOdds * 100)
  };

  try {
    const response = await fetch('/bet', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      throw new Error(`Server returned ${response.status}`);
    }

    const data = await response.json();
    console.log('Server response:', data);

    amountInput.value = '';
    oddsInitialized = false;

  } catch (error) {
    console.error('Error submitting bet:', error);
  }
});

// websocket
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    // render num matched
    document.getElementById("num-matched").textContent = data.num_matched;

    // render fair odds - format for display
    fairOdds = (data.fair_odds / 100).toFixed(2);
    document.getElementById("fair-odds").textContent = fairOdds;
    
    // update chart - unscale the data arrays
    chart.data.datasets[0].data = data.liq_um_lay.map(v => v / 100);
    chart.data.datasets[1].data = data.liq_um_back.map(v => v / 100);
    chart.data.datasets[2].data = data.liq_ma.map(v => -v / 100);
    chart.data.labels = data.odds.map(o => (o / 100).toFixed(2));
    chart.update();

    // update recommended odds
    if (!oddsInitialized) {
        if (backRadio.checked) {
            if (data.max_lay != 0) {
                oddsInput.value = (data.max_lay / 100).toFixed(2);
            }
        }
        else {
            if (data.min_back != 0) {
                oddsInput.value = (data.min_back / 100).toFixed(2);
            }
        }
        oddsInitialized = true;
        updateLiability();
    }
};

ws.onopen = () => console.log("Connected to stream");
ws.onclose = () => console.log("Disconnected");
