document.addEventListener('DOMContentLoaded', function() {
    // Expense Chart
    const expenseCtx = document.getElementById('expenseChart');
    if (expenseCtx) {
        new Chart(expenseCtx, {
            type: 'pie',
            data: {
                labels: ['Food', 'Rent', 'Utilities', 'Entertainment', 'Other'],
                datasets: [{
                    data: [300, 1000, 200, 100, 150],
                    backgroundColor: [
                        'rgba(255, 99, 132, 0.8)',
                        'rgba(54, 162, 235, 0.8)',
                        'rgba(255, 206, 86, 0.8)',
                        'rgba(75, 192, 192, 0.8)',
                        'rgba(153, 102, 255, 0.8)'
                    ]
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    title: {
                        display: true,
                        text: 'Expense Breakdown'
                    }
                }
            }
        });
    }

    // Income vs Expense Chart
    const incomeVsExpenseCtx = document.getElementById('incomeVsExpenseChart');
    if (incomeVsExpenseCtx) {
        new Chart(incomeVsExpenseCtx, {
            type: 'bar',
            data: {
                labels: ['January', 'February', 'March', 'April', 'May', 'June'],
                datasets: [{
                    label: 'Income',
                    data: [3000, 3200, 3100, 3400, 3300, 3500],
                    backgroundColor: 'rgba(75, 192, 192, 0.8)'
                }, {
                    label: 'Expenses',
                    data: [2500, 2700, 2600, 2800, 2900, 3000],
                    backgroundColor: 'rgba(255, 99, 132, 0.8)'
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    title: {
                        display: true,
                        text: 'Income vs Expenses'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Amount ($)'
                        }
                    }
                }
            }
        });
    }

    // Update goals progress
    const goals = document.querySelectorAll('.goal-card');
    goals.forEach(goal => {
        const progress = goal.querySelector('progress');
        const current = parseFloat(progress.value);
        const target = parseFloat(progress.max);
        const percentage = (current / target) * 100;
        goal.style.background = `linear-gradient(to right, #4CAF50 ${percentage}%, #f4f4f4 ${percentage}%)`;
    });
});


