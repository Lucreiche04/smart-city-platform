// Mini-plugin Chart.js qui trace une ligne horizontale au niveau du seuil.
// (Évite d'ajouter la dépendance chartjs-plugin-annotation pour une seule ligne.)
export default {
  id: 'thresholdLine',
  afterDatasetsDraw(chart, _args, opts) {
    if (!opts?.value) return
    const { ctx, chartArea, scales } = chart
    const y = scales.y.getPixelForValue(opts.value)
    if (y < chartArea.top || y > chartArea.bottom) return
    ctx.save()
    ctx.strokeStyle = '#d63b3b'
    ctx.setLineDash([6, 4])
    ctx.beginPath()
    ctx.moveTo(chartArea.left, y)
    ctx.lineTo(chartArea.right, y)
    ctx.stroke()
    ctx.restore()
  },
}
