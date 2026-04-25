// Create status chart
const ctx = document.getElementById('statusChart');
if (ctx) {
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['KSA Services', 'QA Services'],
            datasets: [{
                data: [ksaServices, qaServices],
                backgroundColor: [
                    '#2c3e50',  // Saudi green
                    '#8b4513'   // Qatar maroon
                ],
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.label + ': ' + context.parsed;
                        }
                    }
                }
            }
        }
    });
}
