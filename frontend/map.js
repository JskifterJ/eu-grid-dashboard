// EU Grid Map — D3 + world-atlas TopoJSON
// Exposes window.initMap and window.drawFlowArrows as globals

const EUROPEAN_IDS = new Set([
  '276','250','826','578','752','208','246','756','40','528','56','616',
  '724','380','203','620','642','300','372','348','703','705','688','191',
  '440','428','233','804','442','100','8','499','70','807','352','196',
]);

const COUNTRY_MAP = {
  '276':'DE','250':'FR','826':'GB','578':'NO','752':'SE','208':'DK',
  '246':'FI','756':'CH','40':'AT','528':'NL','56':'BE','616':'PL',
  '724':'ES','380':'IT','203':'CZ','620':'PT','642':'RO','300':'GR',
  '372':'IE','348':'HU','233':'EE','428':'LV','440':'LT','703':'SK',
  '705':'SI','191':'HR','100':'BG','688':'RS','70':'BA','499':'ME',
  '807':'MK','8':'AL','352':'IS','196':'CY','442':'LU',
};

const CENTROIDS = {
  'DE':[10.5,51.2],'FR':[2.2,46.6],'GB':[-2.5,53.5],'NO':[10,62],
  'SE':[16,62],'DK':[10,56],'FI':[26,63],'CH':[8.2,46.8],
  'AT':[14.5,47.6],'NL':[5.2,52.2],'BE':[4.4,50.5],'PL':[20,52],
  'ES':[-3.5,40],'IT':[12.5,42.5],'CZ':[15.5,49.8],'PT':[-8,39.5],
  'RO':[25,45.9],'GR':[22,39.5],'IE':[-8,53.2],'HU':[19,47.2],
  'EE':[25,58.6],'LV':[24.6,56.9],'LT':[23.9,55.2],'SK':[19.7,48.7],
  'SI':[15,46.1],'HR':[15.2,45.1],'BG':[25.5,42.7],'RS':[21,44],
  'BA':[17.7,43.9],'ME':[19.4,42.7],'MK':[21.8,41.6],'AL':[20.2,41.1],
  'IS':[-19,65],'CY':[33.4,35.1],'LU':[6.1,49.8],
};

window.MAP_FLAGS = {
  'DE':'🇩🇪','FR':'🇫🇷','GB':'🇬🇧','NO':'🇳🇴','SE':'🇸🇪','DK':'🇩🇰',
  'FI':'🇫🇮','CH':'🇨🇭','AT':'🇦🇹','NL':'🇳🇱','BE':'🇧🇪','PL':'🇵🇱',
  'ES':'🇪🇸','IT':'🇮🇹','CZ':'🇨🇿','PT':'🇵🇹','RO':'🇷🇴','GR':'🇬🇷',
  'IE':'🇮🇪','HU':'🇭🇺','EE':'🇪🇪','LV':'🇱🇻','LT':'🇱🇹','SK':'🇸🇰',
  'SI':'🇸🇮','HR':'🇭🇷','BG':'🇧🇬','RS':'🇷🇸','BA':'🇧🇦','ME':'🇲🇪',
  'MK':'🇲🇰','AL':'🇦🇱','IS':'🇮🇸','CY':'🇨🇾','LU':'🇱🇺',
};

window.MAP_NAMES = {
  'DE':'Germany','FR':'France','GB':'United Kingdom','NO':'Norway','SE':'Sweden',
  'DK':'Denmark','FI':'Finland','CH':'Switzerland','AT':'Austria','NL':'Netherlands',
  'BE':'Belgium','PL':'Poland','ES':'Spain','IT':'Italy','CZ':'Czech Republic',
  'PT':'Portugal','RO':'Romania','GR':'Greece','IE':'Ireland','HU':'Hungary',
  'EE':'Estonia','LV':'Latvia','LT':'Lithuania','SK':'Slovakia',
  'SI':'Slovenia','HR':'Croatia','BG':'Bulgaria','RS':'Serbia',
  'BA':'Bosnia & Herzegovina','ME':'Montenegro','MK':'North Macedonia',
  'AL':'Albania','IS':'Iceland','CY':'Cyprus','LU':'Luxembourg',
};

window.GEN_COLORS = {
  Wind:'#3fb950',Solar:'#d29922',Nuclear:'#58a6ff',Hydro:'#79c0ff','Hydro Reservoir':'#58c4ff',
  'Pumped Storage':'#4aa8e0',Gas:'#f78166',Coal:'#6e7681',Lignite:'#555',
  Biomass:'#a5d6ff',Other:'#30363d','Other Renewable':'#5dade2',
};

function _isLight() {
  return document.documentElement.dataset.theme === 'light';
}
function co2Fill(v) {
  return _isLight()
    ? d3.scaleLinear().domain([0,150,400,700]).range(['#c6eed0','#faefc6','#faddd8','#f7c5c0']).clamp(true)(v)
    : d3.scaleLinear().domain([0,150,400,700]).range(['#1e5c30','#3d5018','#5c3a0a','#5c1818']).clamp(true)(v);
}
function co2Stroke(v) {
  return _isLight()
    ? d3.scaleLinear().domain([0,150,400,700]).range(['#2da042','#c28a00','#e03428','#e03428']).clamp(true)(v)
    : d3.scaleLinear().domain([0,150,400,700]).range(['#3fb950','#d29922','#f85149','#f85149']).clamp(true)(v);
}

let _projection, _svgG, _overviewByCode = {}, _zoomBehavior = null;

window.initMap = async function(onCountrySelect) {
  const world = await fetch('https://cdn.jsdelivr.net/npm/world-atlas@2/countries-50m.json').then(r => r.json());
  const countries = topojson.feature(world, world.objects.countries);
  const euroFeatures = countries.features.filter(f => EUROPEAN_IDS.has(String(+f.id)));

  const container = document.getElementById('map-svg');
  const W = container.parentElement.clientWidth - 24 || 560;
  const H = 380;
  container.setAttribute('viewBox', `0 0 ${W} ${H}`);
  container.setAttribute('height', H);

  _projection = d3.geoMercator().center([14, 56]).scale(W * 0.95).translate([W / 2, H / 2]);
  const path = d3.geoPath().projection(_projection);
  const svg = d3.select('#map-svg');

  svg.append('defs').html(`
    <marker id="arrowBlue" markerWidth="5" markerHeight="5" refX="4" refY="2.5" orient="auto">
      <path d="M0,0 L5,2.5 L0,5 Z" fill="#58a6ff" opacity="0.8"/>
    </marker>
    <marker id="arrowOrange" markerWidth="5" markerHeight="5" refX="4" refY="2.5" orient="auto">
      <path d="M0,0 L5,2.5 L0,5 Z" fill="#f78166" opacity="0.8"/>
    </marker>
  `);

  _svgG = svg.append('g');

  // Pan + zoom
  const zoom = d3.zoom()
    .scaleExtent([1, 8])
    .translateExtent([[-W * 0.3, -H * 0.3], [W * 1.3, H * 1.3]])
    .on('zoom', (event) => { _svgG.attr('transform', event.transform); });
  svg.call(zoom).on('dblclick.zoom', null);  // double-click doesn't zoom; we'll use it for reset
  _zoomBehavior = zoom;  // store for reset button

  _svgG.append('rect').attr('class', 'map-ocean').attr('width', W).attr('height', H).attr('rx', 6);

  _svgG.selectAll('.country')
    .data(euroFeatures)
    .join('path')
    .attr('class', 'country country-base')
    .attr('d', path)
    .attr('stroke', 'var(--border)')
    .on('click', function(event, d) {
      const code = COUNTRY_MAP[String(+d.id)];
      if (!code) return;
      _selectCountry(code, euroFeatures, onCountrySelect);
    });

  _svgG.selectAll('.country-label')
    .data(euroFeatures.filter(d => CENTROIDS[COUNTRY_MAP[String(+d.id)]]))
    .join('text')
    .attr('class', 'country-label').style('font-size', '7.5px').style('fill', 'var(--dim)')
    .style('pointer-events', 'none').style('text-anchor', 'middle')
    .attr('x', d => _projection(CENTROIDS[COUNTRY_MAP[String(+d.id)]])[0])
    .attr('y', d => _projection(CENTROIDS[COUNTRY_MAP[String(+d.id)]])[1] + 3)
    .text(d => COUNTRY_MAP[String(+d.id)] || '');

  _addDenmarkPin();

  // Load overview to colour countries
  try {
    const overview = await window.fetchOverview();
    overview.countries.forEach(c => { _overviewByCode[c.country] = c; });
    d3.selectAll('.country').data(euroFeatures).each(function(d) {
      const code = COUNTRY_MAP[String(+d.id)];
      const info = _overviewByCode[code];
      if (info) {
        d3.select(this).attr('fill', co2Fill(info.co2_intensity)).attr('stroke', co2Stroke(info.co2_intensity));
      }
    });
  } catch(e) { console.warn('Overview fetch failed:', e); }

  // Background flow web — all bilateral imports/exports as thin lines.
  try {
    const allFlows = await window.fetchAllFlows(Object.keys(window.MAP_NAMES));
    const seenEdges = new Set();
    allFlows.forEach(({country, flows}) => {
      if (!flows) return;
      const fromPos = CENTROIDS[country];
      if (!fromPos) return;
      const [x1, y1] = _projection(fromPos);
      flows.forEach(flow => {
        const partnerCode = Object.entries(window.MAP_NAMES).find(([k, v]) => v === flow.partner)?.[0];
        if (!partnerCode || !CENTROIDS[partnerCode]) return;
        // dedupe undirected edges so we draw each line only once
        const edgeKey = [country, partnerCode].sort().join('—');
        if (seenEdges.has(edgeKey)) return;
        seenEdges.add(edgeKey);
        const [x2, y2] = _projection(CENTROIDS[partnerCode]);
        const mx = (x1 + x2) / 2 + (y2 - y1) * 0.18;
        const my = (y1 + y2) / 2 - (x2 - x1) * 0.18;
        _svgG.insert('path', '.country')
          .attr('class', 'flow-web')
          .attr('d', `M${x1},${y1} Q${mx},${my} ${x2},${y2}`)
          .attr('fill', 'none')
          .attr('stroke', 'var(--accent)')
          .attr('stroke-width', Math.min(2.2, 0.5 + flow.flow_gw * 0.3))
          .attr('opacity', 0.18);
      });
    });
  } catch (e) { console.warn('flow web fetch failed:', e); }

  await _loadDatacenters();
  _renderDatacenters();
  _wireDatacenterToggles();

  // Default: Denmark
  _selectCountry('DK', euroFeatures, onCountrySelect);

  return function selectCountry(code) { _selectCountry(code, euroFeatures, onCountrySelect); };
};

function _selectCountry(code, euroFeatures, onCountrySelect) {
  d3.selectAll('.country').classed('selected', false);
  d3.selectAll('.country').filter(d => COUNTRY_MAP[String(+d.id)] === code).classed('selected', true);
  const sel = document.getElementById('country-select');
  if (sel) sel.value = code;
  onCountrySelect(code);
}

function _addDenmarkPin() {
  const dkPos = _projection(CENTROIDS['DK']);
  const px = dkPos[0] + 4, py = dkPos[1] - 18;

  const pulse = _svgG.append('circle')
    .attr('cx', px).attr('cy', py + 14).attr('r', 5)
    .attr('fill', 'none').attr('stroke', '#7ee787').attr('stroke-width', 1.2).attr('opacity', 0.8);

  (function loop() {
    pulse.attr('r', 5).attr('opacity', 0.8)
      .transition().duration(1400).attr('r', 13).attr('opacity', 0).on('end', loop);
  })();

  _svgG.append('circle').attr('cx', px).attr('cy', py + 14).attr('r', 3.5).attr('fill', '#7ee787');

  const bubble = _svgG.append('g').attr('transform', `translate(${px}, ${py})`);
  const bw = 92, bh = 32, br = 5;
  bubble.append('path')
    .attr('d', `M${-bw/2+br},${-bh} h${bw-2*br} a${br},${br} 0 0 1 ${br},${br} v${bh-2*br} a${br},${br} 0 0 1 ${-br},${br} h${-bw/2+br+6} l-6,7 l-6,-7 h${-bw/2+br+6} a${br},${br} 0 0 1 ${-br},${-br} v${-bh+2*br} a${br},${br} 0 0 1 ${br},${-br} z`)
    .attr('fill', '#0d2016').attr('stroke', '#7ee787').attr('stroke-width', 1);
  const label = bubble.append('text').attr('text-anchor', 'middle').attr('font-size', '9').attr('fill', '#7ee787').attr('font-family', 'system-ui,sans-serif');
  label.append('tspan').attr('x', 0).attr('y', -bh + 11).text("🏠 that's where");
  label.append('tspan').attr('x', 0).attr('dy', 12).text("I'm from 😄");
}

window.drawFlowArrows = function(flows, fromCountry) {
  _svgG.selectAll('.flow-arrow').remove();
  if (!flows || !fromCountry) return;
  const selPos = CENTROIDS[fromCountry];
  if (!selPos) return;
  const [sx, sy] = _projection(selPos);

  flows.forEach(flow => {
    const partnerCode = Object.entries(window.MAP_NAMES).find(([k, v]) => v === flow.partner)?.[0];
    if (!partnerCode || !CENTROIDS[partnerCode]) return;
    const [px, py] = _projection(CENTROIDS[partnerCode]);

    // Geometry: source = origin of flow, dest = receiver
    const isExport = flow.direction === 'export';
    const [x1, y1, x2, y2] = isExport ? [sx, sy, px, py] : [px, py, sx, sy];

    const mx = (x1 + x2) / 2 + (y2 - y1) * 0.2;
    const my = (y1 + y2) / 2 - (x2 - x1) * 0.2;

    _svgG.append('path')
      .attr('class', 'flow-arrow')
      .attr('d', `M${x1},${y1} Q${mx},${my} ${x2},${y2}`)
      .attr('fill', 'none')
      .attr('stroke', isExport ? '#f78166' : '#58a6ff')
      .attr('stroke-width', 1.4).attr('opacity', 0.7)
      .attr('marker-end', isExport ? 'url(#arrowOrange)' : 'url(#arrowBlue)');
  });
};

window.updateMapTheme = function() {
  if (!_svgG) return;
  // Re-colour countries using current theme's co2Fill/co2Stroke
  d3.selectAll('.country').each(function(d) {
    const code = COUNTRY_MAP[String(+d.id)];
    const info = _overviewByCode[code];
    if (info) {
      d3.select(this).attr('fill', co2Fill(info.co2_intensity)).attr('stroke', co2Stroke(info.co2_intensity));
    }
    // Countries with no CO2 data keep CSS fill via class
  });
};

const DC_COLORS = { 'hyperscaler': '#58a6ff', 'neocloud': '#d2a8ff', 'ai-factory': '#9cc98a' };
const DC_RADIUS = { 'hyperscaler': 2.5, 'neocloud': 2.8, 'ai-factory': 3.4 };
let _datacenters = [];
const _dcVisible = { 'hyperscaler': true, 'neocloud': true, 'ai-factory': true };

async function _loadDatacenters() {
  try {
    const r = await fetch('/datacenters.json');
    const data = await r.json();
    _datacenters = data.datacenters || [];
  } catch (e) { console.warn('dc load failed:', e); }
}

function _renderDatacenters() {
  if (!_svgG) return;
  _svgG.selectAll('.dc-marker').remove();
  _datacenters.forEach(dc => {
    if (!_dcVisible[dc.type]) return;
    const [x, y] = _projection([dc.lon, dc.lat]);
    if (Number.isNaN(x) || Number.isNaN(y)) return;
    const g = _svgG.append('g').attr('class', 'dc-marker');
    g.append('circle')
      .attr('cx', x).attr('cy', y)
      .attr('r', DC_RADIUS[dc.type])
      .attr('fill', DC_COLORS[dc.type])
      .attr('opacity', 0.85)
      .attr('stroke', 'rgba(0,0,0,0.4)')
      .attr('stroke-width', 0.4);
    g.append('title').text(`${dc.name} · ${dc.operator}${dc.notes ? ' · ' + dc.notes : ''}`);
  });
}

function _wireDatacenterToggles() {
  ['hyperscaler', 'neocloud', 'ai-factory'].forEach(t => {
    const el = document.getElementById(`dc-toggle-${t}`);
    if (!el) return;
    el.addEventListener('change', () => {
      _dcVisible[t] = el.checked;
      _renderDatacenters();
    });
  });
}

window.resetMapView = function() {
  if (_zoomBehavior) {
    d3.select('#map-svg').transition().duration(400).call(_zoomBehavior.transform, d3.zoomIdentity);
  }
};
