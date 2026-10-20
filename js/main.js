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
        ctx.strokeStyle = 'white';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(px, top);
        ctx.lineTo(px, bottom);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle = 'white';
        ctx.restore();
    }
}


// chart initialization
Chart.defaults.color = 'white';

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
        borderColor: 'rgba(0, 0, 128, 0)',
        backgroundColor: 'rgba(228, 116, 0, 0.7)',
        borderWidth: 1.5,
        pointRadius: 0,
        color: 'white'
    },
    {
        label: 'back',
        data: [],
        stepped: 'middle',
        fill: 'origin',
        borderColor: 'rgba(0, 0, 128, 0)',
        backgroundColor: 'rgba(0, 116, 228, 0.7)',
        borderWidth: 1.5,
        pointRadius: 0,
        color: 'white'
    },
    {
        label: 'matched',
        data: [],
        stepped: 'middle',
        fill: 'origin',
        borderColor: 'rgba(255, 159, 64, 0)',
        backgroundColor: 'rgba(255, 255, 255, 0.7)',
        borderWidth: 1.5,
        pointRadius: 0,
        color: 'white'
    },
    ],
},
options: {
    color: 'white',
    responsive: true,
    layout: { padding: { top: 20 } },
    interaction: { mode: 'index', intersect: false },
    animation: {
        duration: 100
    },
    scales: {
    x: { title: { display: true, text: 'lay ◀ odds ▶ back', color: 'white' , font: {size: 14} },
        grid: {color: 'rgba(255, 255, 255, 0.1)' },
        border: {display: false },
        display: true,
    },
    y: {
        // Intercept the data limits before the chart generates ticks
        afterDataLimits: (scale) => {
            // Find the absolute largest value in your current data
            const maxLimit = Math.max(Math.abs(scale.max), Math.abs(scale.min));
            
            // Force the scale to be perfectly symmetrical around 0
            scale.max = maxLimit;
            scale.min = -maxLimit;
        },
        title: { display: true, text: 'liquidity', color: 'white', font: {size: 14} },
        ticks: { callback: v => Math.abs(v).toLocaleString(), color: 'white' },
        grid: {color: 'rgba(255, 255, 255, 0.1)' },
        border: { display: false },
    },
    },
    plugins: {
        tooltip: {
            callbacks: {
            label: c => `${c.dataset.label}: ${Math.abs(c.parsed.y).toLocaleString()}`,
            color: 'white'
            },
            color: 'white',
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
        // lay bet
        l = (odds - 1) * stake;
    }
    else {
        // back bet
        l = stake;
    }

    return l;
}


function updateLiability () {
    // calculate liability after odds change
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

  // gather input
  const isBack = document.getElementById('backRadio').checked;
  const betAmount = parseFloat(document.getElementById('amountInput').value);
  const betOdds = parseFloat(document.getElementById('oddsInput').value);

  // create payload
  const payload = {
    is_back: isBack,        // boolean: true / false
    bet_amount: betAmount,  // float
    bet_odds: betOdds       // float
  };

  // send payload
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

    // reset form
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

    // render fair odds
    fairOdds = data.fair_odds;
    document.getElementById("fair-odds").textContent = data.fair_odds;
    
    // update chart
    chart.data.datasets[0].data = data.liq_um_lay;
    chart.data.datasets[1].data = data.liq_um_back;
    chart.data.datasets[2].data = data.liq_ma.map((v) => -v);
    chart.data.labels = data.odds;
    chart.update();

    // update recommended odds
    if (!oddsInitialized) {
        
        if (backRadio.checked) {
            // back
            if (data.max_lay != 0) {
                oddsInput.value = data.max_lay;
            }
        }
        else {
            // lay
            if (data.min_back != 0) {
                oddsInput.value = data.min_back;
            }
        }

        oddsInitialized = true;
        updateLiability();
    }
};

ws.onopen = () => console.log("Connected to stream");
ws.onclose = () => console.log("Disconnected");