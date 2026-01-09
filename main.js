document.addEventListener('DOMContentLoaded', function() {

    const chartDom = document.getElementById('chart');
    const fanListDom = document.getElementById('fan-list');
    const projectSelectDom = document.getElementById('project-select');
    const selectAllCheckbox = document.getElementById('select-all-checkbox');
    const fanSearchInput = document.getElementById('fan-search');
    const clearSearchBtn = document.getElementById('clear-search');

    const myChart = echarts.init(chartDom);

    // 收藏功能
    let favorites = JSON.parse(localStorage.getItem('fanFavorites') || '[]');

    // 检测是否为移动设备
    function isMobile() {
        return window.innerWidth <= 768;
    }

    // 获取响应式配置
    function getResponsiveConfig() {
        const mobile = isMobile();
        return {
            grid: {
                right: mobile ? '5%' : '12%',
                left: mobile ? '15%' : '10%',
                bottom: mobile ? '30%' : '10%',  // 增加移动端底部间距
                top: mobile ? '12%' : '10%'
            },
            xAxis: {
                nameLocation: 'middle',
                nameGap: mobile ? 35 : 25,
                nameTextStyle: {
                    fontSize: mobile ? 12 : 14,
                    fontWeight: 'bold'
                },
                axisLabel: {
                    fontSize: mobile ? 10 : 12
                }
            },
            yAxis: {
                nameLocation: 'middle',
                nameGap: mobile ? 50 : 45,
                nameTextStyle: {
                    fontSize: mobile ? 12 : 14,
                    fontWeight: 'bold'
                },
                axisLabel: {
                    fontSize: mobile ? 10 : 12,
                    formatter: function (value) {
                        return value.toFixed(2);
                    }
                }
            },
            legend: {
                orient: mobile ? 'horizontal' : 'vertical',
                [mobile ? 'bottom' : 'right']: mobile ? '2%' : '2%',  // 移动端图例位置稍微上移
                [mobile ? 'left' : 'top']: mobile ? 'center' : 'center',
                width: mobile ? '95%' : '20%',  // 增加移动端图例宽度
                type: 'scroll',
                pageIconSize: mobile ? 12 : 14,  // 增大移动端翻页按钮
                pageTextStyle: {
                    fontSize: mobile ? 10 : 12
                },
                textStyle: {
                    fontSize: mobile ? 11 : 14  // 稍微增大移动端字体
                },
                itemGap: mobile ? 8 : 10,  // 移动端图例项间距
                itemWidth: mobile ? 20 : 25,  // 移动端图例图标宽度
                itemHeight: mobile ? 12 : 14,  // 移动端图例图标高度
                // 添加选择器
                selector: [
                    {
                        type: 'all',
                        title: '全选'
                    },
                    {
                        type: 'inverse',
                        title: '反选'
                    }
                ],
                selectorLabel: {
                    fontSize: mobile ? 10 : 12
                }
            },
            title: {
                textStyle: {
                    fontSize: mobile ? 14 : 18
                }
            }
        };
    }

    // 预定义的基础颜色池（移除淡色，保留饱和度高的颜色）
    const baseColors = [
        '#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de',
        '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc', '#d14a61',
        '#6e7074', '#546570',
        '#ff6b6b', '#4ecdc4', '#45b7d1', '#f9ca24', '#6ab04c',
        '#badc58', '#f0932b', '#eb4d4b', '#c44569', '#574b90',
        '#f8b500', '#00d2d3', '#1e3799', '#b71540', '#079992',
        '#38ada9', '#78e08f', '#fa983a', '#e55039', '#4a69bd',
        '#60a3bc', '#e58e26', '#f53b57', '#3c40c6', '#0fbcf9',
        '#ffa801', '#05c46b', '#ffd32a', '#ff3f34', '#00d8d6',
        '#e74c3c', '#9b59b6', '#3498db', '#1abc9c', '#f39c12',
        '#d35400', '#c0392b', '#8e44ad', '#2980b9', '#27ae60',
        '#16a085', '#f1c40f', '#e67e22', '#e84393', '#6c5ce7',
        '#fd79a8', '#fdcb6e', '#00b894', '#0984e3', '#d63031'
    ];

    // 动态生成颜色的函数（当基础颜色不够时使用）
    function generateColor(index) {
        if (index < baseColors.length) {
            return baseColors[index];
        }
        
        // 使用HSL颜色空间生成不重复的颜色
        // 通过改变色相(Hue)来生成不同颜色
        const hue = (index * 137.508) % 360; // 使用黄金角度分布
        const saturation = 65 + (index % 3) * 10; // 65-85%
        const lightness = 50 + (index % 4) * 5; // 50-65%
        
        return `hsl(${hue}, ${saturation}%, ${lightness}%)`;
    }

    // 生成足够多的颜色（支持最多100个不同的颜色）
    const colors = Array.from({ length: 100 }, (_, i) => generateColor(i));

    const option = {
        color: colors,
        title: {
            text: '', // Title will be set dynamically
            left: 'center'
        },
        tooltip: {
            trigger: 'axis',
            axisPointer: {
                type: 'cross',
                label: {
                    backgroundColor: '#6a7985'
                }
            },
            confine: true, // 限制在图表区域内
            formatter: function (params) {
                if (!params || params.length === 0) return '';
                
                const noise = params[0].value[0];
                let result = `<div style="padding: 5px;">`;
                result += `<strong style="font-size: 14px;">噪声: ${noise} dBA</strong><br/>`;
                result += `<div style="margin-top: 8px; max-height: 300px; overflow-y: auto;">`;
                
                // 按温度排序
                const sortedParams = [...params].sort((a, b) => a.value[1] - b.value[1]);
                
                sortedParams.forEach((item, index) => {
                    const temp = item.value[1];
                    const speed = item.value[2];
                    
                    // 排名标记
                    let rankBadge = '';
                    if (index === 0) {
                        rankBadge = '<span style="color: #27ae60; font-weight: bold;">🥇</span> ';
                    } else if (index === 1) {
                        rankBadge = '<span style="color: #95a5a6; font-weight: bold;">🥈</span> ';
                    } else if (index === 2) {
                        rankBadge = '<span style="color: #cd7f32; font-weight: bold;">🥉</span> ';
                    } else {
                        rankBadge = `<span style="color: #999;">#${index + 1}</span> `;
                    }
                    
                    result += `<div style="margin: 4px 0; padding: 4px; border-left: 3px solid ${item.color}; padding-left: 8px;">`;
                    result += rankBadge;
                    result += `${item.marker} <strong>${item.seriesName}</strong><br/>`;
                    result += `<span style="margin-left: 20px;">温度: <strong>${temp}℃</strong></span>`;
                    
                    if (speed !== undefined) {
                        result += `<br/><span style="margin-left: 20px; color: #666;">转速: ${speed} RPM</span>`;
                    }
                    result += `</div>`;
                });
                
                result += `</div></div>`;
                return result;
            },
            backgroundColor: 'rgba(255, 255, 255, 0.95)',
            borderColor: '#ccc',
            borderWidth: 1,
            textStyle: {
                color: '#333'
            }
        },

        legend: {
            // data: [],
            orient: 'vertical',
            right: '2%',
            top: 'center',
            width: '20%',
            textStyle: {
                fontSize: 14
            },
            type: 'scroll',
            pageIconSize: 14,
            pageTextStyle: {
                fontSize: 12
            }
        },

        grid: {
            right: '12%',
            containLabel: false
        },

        xAxis: {
            name: '噪声 (dBA)',
            type: 'value',
            scale: true,
            nameLocation: 'middle',
            nameGap: 25
        },

        yAxis: {
            name: '温度 (℃)',
            type: 'value',
            scale: true,
            nameLocation: 'middle',
            nameGap: 45,
            axisLabel: {
                formatter: function (value) {
                    return value.toFixed(2);
                }
            }
        },

        dataZoom: [
            {
                type: 'inside',
                filterMode: 'none'  // 不过滤数据，确保所有点都参与连线
            },
//            { type: 'slider' }
        ],

        series: []
    };

    myChart.setOption(option);

    let allFanData = {};
    let projects = [];
    let currentProject = null;

    function loadProjectData(project) {
        currentProject = project;
        // Clear previous data
        allFanData = {};
        fanListDom.innerHTML = '';
        selectAllCheckbox.checked = false;
        myChart.setOption({ series: [] });

        // 更新header中的项目描述
        const descriptionDom = document.getElementById('project-description');
        if (descriptionDom && project.description) {
            descriptionDom.innerHTML = project.description;
        } else if (descriptionDom) {
            descriptionDom.innerHTML = '';
        }

        // 获取响应式配置
        const responsiveConfig = getResponsiveConfig();
        
        // Update chart title and axes with responsive config
        myChart.setOption({
            title: {
                text: project.title,
                ...responsiveConfig.title
            },
            xAxis: {
                name: project.xAxisName,
                ...responsiveConfig.xAxis
            },
            yAxis: {
                name: project.yAxisName,
                ...responsiveConfig.yAxis
            },
            grid: responsiveConfig.grid,
            legend: responsiveConfig.legend
        });

        fetch(project.dataFile)
            .then(response => response.json())
            .then(data => {
                allFanData = data;
                const fanNames = Object.keys(data);

                fanNames.forEach(name => {
                    const label = document.createElement('label');
                    const checkbox = document.createElement('input');

                    checkbox.type = 'checkbox';
                    checkbox.value = name;
                    checkbox.checked = true; // 默认选中所有风扇
                    checkbox.addEventListener('change', () => {
                        updateSelectAllState();
                        updateChart();
                    });

                    label.appendChild(checkbox);
                    label.appendChild(document.createTextNode(' ' + name));
                    fanListDom.appendChild(label);
                });

                // 更新全选复选框状态
                selectAllCheckbox.checked = true;
                selectAllCheckbox.indeterminate = false;

                // 添加收藏按钮
                updateFavoriteButtons();
                updateFavoritesList();

                // 自动更新图表显示所有图线
                updateChart();
            })
            .catch(error => {
                console.error(`加载 ${project.dataFile} 文件失败:`, error);
                fanListDom.innerHTML = `<p style='color: red;'>加载项目数据失败，请检查 ${project.dataFile} 文件。</p>`;
            });
    }

    // 从URL路径加载项目
    function loadProjectFromPath() {
        const path = window.location.pathname;
        if (path && path !== '/') {
            // 移除开头的斜杠
            const projectName = decodeURIComponent(path.substring(1));
            const project = projects.find(p => p.name === projectName);
            if (project) {
                projectSelectDom.value = project.name;
                loadProjectData(project);
                return true;
            }
        }
        return false;
    }

    // 更新URL路径
    function updatePath(projectName) {
        const newPath = '/' + encodeURIComponent(projectName);
        window.history.pushState({ project: projectName }, '', newPath);
    }

    fetch('projects.json')
        .then(response => response.json())
        .then(data => {
            projects = data;
            if (projects.length > 0) {
                projects.forEach(proj => {
                    const option = document.createElement('option');
                    option.value = proj.name;
                    option.textContent = proj.name;
                    projectSelectDom.appendChild(option);
                });
                
                projectSelectDom.addEventListener('change', (e) => {
                    const selectedProjectName = e.target.value;
                    const selectedProject = projects.find(p => p.name === selectedProjectName);
                    if (selectedProject) {
                        updatePath(selectedProjectName);
                        loadProjectData(selectedProject);
                    }
                });

                // 监听浏览器前进/后退按钮
                window.addEventListener('popstate', () => {
                    loadProjectFromPath();
                });

                // 页面加载时尝试从URL加载项目，如果没有则加载第一个
                if (!loadProjectFromPath()) {
                    updatePath(projects[0].name);
                    loadProjectData(projects[0]);
                }
            } else {
                 fanListDom.innerHTML = "<p style='color: red;'>未找到任何项目，请检查projects.json文件。</p>";
            }
        })
        .catch(error => {
            console.error("加载projects.json文件失败:", error);
            fanListDom.innerHTML = "<p style='color: red;'>加载项目配置失败，请检查projects.json文件是否存在。</p>";
        });

    selectAllCheckbox.addEventListener('change', () => {
        const fanCheckboxes = fanListDom.querySelectorAll('input[type="checkbox"]');
        fanCheckboxes.forEach(checkbox => {
            checkbox.checked = selectAllCheckbox.checked;
        });
        updateChart();
    });

    function updateSelectAllState() {
        const fanCheckboxes = fanListDom.querySelectorAll('input[type="checkbox"]');
        const allChecked = [...fanCheckboxes].every(checkbox => checkbox.checked);
        const noneChecked = [...fanCheckboxes].every(checkbox => !checkbox.checked);

        if (allChecked) {
            selectAllCheckbox.checked = true;
            selectAllCheckbox.indeterminate = false;
        } else if (noneChecked) {
            selectAllCheckbox.checked = false;
            selectAllCheckbox.indeterminate = false;
        } else {
            selectAllCheckbox.indeterminate = true;
        }
    }

    function updateChart() {
        const selectedFans = [];
        document.querySelectorAll('#fan-list input[type="checkbox"]:checked').forEach(checkbox => {
            selectedFans.push(checkbox.value);
        });

        const newSeries = selectedFans.map((fanName, index) => {
            const originalData = allFanData[fanName];

            return {
                name: fanName,
                type: 'line',
                smooth: 0.3,
                symbol: 'circle',
                symbolSize: 6,
                clip: false,
                connectNulls: true,  // 连接空值点
                data: originalData,
                itemStyle: {
                    color: colors[index % colors.length]
                },
                lineStyle: {
                    color: colors[index % colors.length]
                },
                emphasis: {           // 添加hover效果
                    focus: 'series',  // 高亮当前系列
                    blurScope: 'coordinateSystem',  // 只在同一坐标系内模糊
                    scale: 1.5        // 放大数据点
                },
                blur: {               // 自定义模糊效果
                    lineStyle: {
                        opacity: 0.2  // 未高亮曲线的透明度（0.3比默认的0.05更清晰）
                    },
                    itemStyle: {
                        opacity: 0.2  // 未高亮数据点的透明度
                    }
                }
            };
        });

        // 获取响应式配置
        const responsiveConfig = getResponsiveConfig();

        myChart.setOption({
            legend: {
                data: selectedFans,
                ...responsiveConfig.legend
            },
            series: newSeries
        }, {
            replaceMerge: 'series'
        });
    }


    window.addEventListener('resize', function() {
        myChart.resize();
        
        // 在窗口大小改变时更新响应式配置
        if (currentProject) {
            const responsiveConfig = getResponsiveConfig();
            myChart.setOption({
                title: responsiveConfig.title,
                xAxis: responsiveConfig.xAxis,
                yAxis: responsiveConfig.yAxis,
                grid: responsiveConfig.grid,
                legend: responsiveConfig.legend
            });
        }
    });

    // 搜索功能
    fanSearchInput.addEventListener('input', function(e) {
        const searchTerm = e.target.value.toLowerCase().trim();
        const fanLabels = fanListDom.querySelectorAll('label');
        
        // 显示/隐藏清除按钮
        clearSearchBtn.style.display = searchTerm ? 'block' : 'none';
        
        fanLabels.forEach(label => {
            const fanName = label.textContent.toLowerCase();
            const matches = fanName.includes(searchTerm);
            
            if (matches) {
                label.classList.remove('fan-item-hidden');
                // 高亮匹配项
                if (searchTerm) {
                    label.classList.add('fan-item-highlight');
                } else {
                    label.classList.remove('fan-item-highlight');
                }
            } else {
                label.classList.add('fan-item-hidden');
                label.classList.remove('fan-item-highlight');
            }
        });
    });

    // 清除搜索
    clearSearchBtn.addEventListener('click', function() {
        fanSearchInput.value = '';
        fanSearchInput.dispatchEvent(new Event('input'));
        fanSearchInput.focus();
    });

    // 收藏功能函数
    function updateFavoritesList() {
        const favList = document.getElementById('favorites-list');
        const showFavBtn = document.getElementById('show-favorites-only');
        
        if (favorites.length === 0) {
            favList.innerHTML = '<span style="color: #999;">暂无收藏，点击风扇名称旁的☆收藏常用风扇</span>';
            showFavBtn.style.display = 'none';
            return;
        }
        
        // 显示"只显示收藏"按钮
        showFavBtn.style.display = 'block';
        
        favList.innerHTML = favorites.map(fan => `
            <span class="favorite-item" data-fan="${fan}" title="点击快速选中此风扇">
                ${fan}
                <span class="remove-fav" onclick="event.stopPropagation(); removeFavorite('${fan}')" title="取消收藏">✕</span>
            </span>
        `).join('');
        
        // 点击收藏项快速选择
        favList.querySelectorAll('.favorite-item').forEach(item => {
            item.addEventListener('click', function(e) {
                if (e.target.classList.contains('remove-fav')) return;
                const fanName = this.dataset.fan;
                
                // 先取消所有选择
                const allCheckboxes = fanListDom.querySelectorAll('input[type="checkbox"]');
                allCheckboxes.forEach(cb => cb.checked = false);
                
                // 只选中点击的收藏项
                const checkbox = Array.from(allCheckboxes).find(cb => cb.value === fanName);
                if (checkbox) {
                    checkbox.checked = true;
                    updateSelectAllState();
                    updateChart();
                    
                    // 滚动到该风扇位置
                    checkbox.parentElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                }
            });
        });
    }

    function toggleFavorite(fanName) {
        const index = favorites.indexOf(fanName);
        if (index > -1) {
            favorites.splice(index, 1);
        } else {
            favorites.push(fanName);
        }
        localStorage.setItem('fanFavorites', JSON.stringify(favorites));
        updateFavoritesList();
        updateFavoriteButtons();
    }

    // 全局函数，供HTML onclick调用
    window.removeFavorite = function(fanName) {
        const index = favorites.indexOf(fanName);
        if (index > -1) {
            favorites.splice(index, 1);
            localStorage.setItem('fanFavorites', JSON.stringify(favorites));
            updateFavoritesList();
            updateFavoriteButtons();
        }
    };

    function updateFavoriteButtons() {
        fanListDom.querySelectorAll('label').forEach(label => {
            const checkbox = label.querySelector('input[type="checkbox"]');
            const fanName = checkbox.value;
            let favBtn = label.querySelector('.favorite-btn');
            
            if (!favBtn) {
                favBtn = document.createElement('span');
                favBtn.className = 'favorite-btn';
                favBtn.innerHTML = '☆';
                favBtn.onclick = (e) => {
                    e.preventDefault();
                    toggleFavorite(fanName);
                };
                label.appendChild(favBtn);
            }
            
            if (favorites.includes(fanName)) {
                favBtn.innerHTML = '★';
                favBtn.classList.add('active');
            } else {
                favBtn.innerHTML = '☆';
                favBtn.classList.remove('active');
            }
        });
    }

    // "只显示收藏"按钮功能
    document.getElementById('show-favorites-only').addEventListener('click', function() {
        // 取消所有选择
        const allCheckboxes = fanListDom.querySelectorAll('input[type="checkbox"]');
        allCheckboxes.forEach(cb => cb.checked = false);
        
        // 只选中收藏的风扇
        favorites.forEach(fanName => {
            const checkbox = Array.from(allCheckboxes).find(cb => cb.value === fanName);
            if (checkbox) {
                checkbox.checked = true;
            }
        });
        
        updateSelectAllState();
        updateChart();
    });

    // 页面加载时初始化收藏列表
    updateFavoritesList();
});
