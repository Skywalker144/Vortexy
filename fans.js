document.addEventListener('DOMContentLoaded', function() {
    let allFans = [];
    let currentFilters = {
        thickness: [],
        bearing: [],
        size: [],
        brand: [],
        search: ''
    };
    let currentSort = 'name-asc';

    // DOM 元素
    const fansGrid = document.getElementById('fans-grid');
    const noResults = document.getElementById('no-results');
    const resultCount = document.getElementById('result-count');
    const searchInput = document.getElementById('search-input');
    const sortSelect = document.getElementById('sort-select');
    const resetBtn = document.getElementById('reset-filters');
    const modal = document.getElementById('fan-modal');
    const modalTitle = document.getElementById('modal-title');
    const modalBody = document.getElementById('modal-body');
    const modalClose = document.querySelector('.modal-close');

    // 加载风扇数据
    fetch('fans_database.json')
        .then(response => response.json())
        .then(data => {
            allFans = data.fans;
            initializeFilters();
            displayFans(allFans);
        })
        .catch(error => {
            console.error('加载风扇数据失败:', error);
            fansGrid.innerHTML = '<p style="color: red; padding: 20px;">加载数据失败，请检查 fans_database.json 文件。</p>';
        });

    // 初始化筛选器
    function initializeFilters() {
        const thicknessSet = new Set();
        const bearingSet = new Set();
        const sizeSet = new Set();
        const brandSet = new Set();

        allFans.forEach(fan => {
            if (fan.thickness) thicknessSet.add(fan.thickness);
            if (fan.bearing) bearingSet.add(fan.bearing);
            if (fan.size) sizeSet.add(fan.size);
            if (fan.brand) brandSet.add(fan.brand);
        });

        createFilterCheckboxes('thickness-filters', Array.from(thicknessSet).sort((a, b) => a - b), 'thickness', 'mm');
        createFilterCheckboxes('bearing-filters', Array.from(bearingSet).sort(), 'bearing');
        createFilterCheckboxes('size-filters', Array.from(sizeSet).sort((a, b) => a - b), 'size', 'mm');
        createFilterCheckboxes('brand-filters', Array.from(brandSet).sort(), 'brand');
    }

    // 创建筛选复选框
    function createFilterCheckboxes(containerId, values, filterType, suffix = '') {
        const container = document.getElementById(containerId);
        container.innerHTML = '';

        values.forEach(value => {
            const label = document.createElement('label');
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.value = value;
            checkbox.addEventListener('change', (e) => {
                updateFilter(filterType, value, e.target.checked);
            });

            label.appendChild(checkbox);
            label.appendChild(document.createTextNode(` ${value}${suffix}`));
            container.appendChild(label);
        });
    }

    // 更新筛选条件
    function updateFilter(filterType, value, isChecked) {
        if (isChecked) {
            if (!currentFilters[filterType].includes(value)) {
                currentFilters[filterType].push(value);
            }
        } else {
            currentFilters[filterType] = currentFilters[filterType].filter(v => v !== value);
        }
        applyFiltersAndSort();
    }

    // 搜索输入事件
    searchInput.addEventListener('input', (e) => {
        currentFilters.search = e.target.value.toLowerCase().trim();
        applyFiltersAndSort();
    });

    // 排序选择事件
    sortSelect.addEventListener('change', (e) => {
        currentSort = e.target.value;
        applyFiltersAndSort();
    });

    // 重置筛选
    resetBtn.addEventListener('click', () => {
        // 清除所有复选框
        document.querySelectorAll('.checkbox-group input[type="checkbox"]').forEach(cb => {
            cb.checked = false;
        });
        
        // 重置筛选条件
        currentFilters = {
            thickness: [],
            bearing: [],
            size: [],
            brand: [],
            search: ''
        };
        
        // 重置搜索框和排序
        searchInput.value = '';
        sortSelect.value = 'name-asc';
        currentSort = 'name-asc';
        
        applyFiltersAndSort();
    });

    // 应用筛选和排序
    function applyFiltersAndSort() {
        let filteredFans = allFans.filter(fan => {
            // 厚度筛选
            if (currentFilters.thickness.length > 0 && !currentFilters.thickness.includes(fan.thickness)) {
                return false;
            }
            
            // 轴承类型筛选
            if (currentFilters.bearing.length > 0 && !currentFilters.bearing.includes(fan.bearing)) {
                return false;
            }
            
            // 尺寸筛选
            if (currentFilters.size.length > 0 && !currentFilters.size.includes(fan.size)) {
                return false;
            }
            
            // 品牌筛选
            if (currentFilters.brand.length > 0 && !currentFilters.brand.includes(fan.brand)) {
                return false;
            }
            
            // 搜索筛选
            if (currentFilters.search && !fan.name.toLowerCase().includes(currentFilters.search)) {
                return false;
            }
            
            return true;
        });

        // 排序
        filteredFans = sortFans(filteredFans, currentSort);

        displayFans(filteredFans);
    }

    // 排序函数
    function sortFans(fans, sortType) {
        const sorted = [...fans];
        
        switch(sortType) {
            case 'name-asc':
                sorted.sort((a, b) => a.name.localeCompare(b.name, 'zh-CN'));
                break;
            case 'name-desc':
                sorted.sort((a, b) => b.name.localeCompare(a.name, 'zh-CN'));
                break;
            case 'thickness-asc':
                sorted.sort((a, b) => (a.thickness || 0) - (b.thickness || 0));
                break;
            case 'thickness-desc':
                sorted.sort((a, b) => (b.thickness || 0) - (a.thickness || 0));
                break;
            case 'size-asc':
                sorted.sort((a, b) => (a.size || 0) - (b.size || 0));
                break;
            case 'size-desc':
                sorted.sort((a, b) => (b.size || 0) - (a.size || 0));
                break;
            case 'brand-asc':
                sorted.sort((a, b) => a.brand.localeCompare(b.brand, 'zh-CN'));
                break;
            case 'brand-desc':
                sorted.sort((a, b) => b.brand.localeCompare(a.brand, 'zh-CN'));
                break;
        }
        
        return sorted;
    }

    // 显示风扇卡片
    function displayFans(fans) {
        fansGrid.innerHTML = '';
        resultCount.textContent = fans.length;

        if (fans.length === 0) {
            noResults.style.display = 'block';
            return;
        }

        noResults.style.display = 'none';

        fans.forEach(fan => {
            const card = createFanCard(fan);
            fansGrid.appendChild(card);
        });
    }

    // 创建风扇卡片
    function createFanCard(fan) {
        const card = document.createElement('div');
        card.className = 'fan-card';
        card.onclick = () => showFanDetails(fan);

        card.innerHTML = `
            <div class="fan-card-header">
                <h3 class="fan-name">${fan.name}</h3>
                <div class="fan-brand">${fan.brand || '未知品牌'}</div>
            </div>
            <div class="fan-specs">
                <div class="spec-row">
                    <span class="spec-label">厚度:</span>
                    <span class="spec-value">${fan.thickness ? fan.thickness + ' mm' : '未知'}</span>
                </div>
                <div class="spec-row">
                    <span class="spec-label">轴承:</span>
                    <span class="spec-value">${fan.bearing || '未知'}</span>
                </div>
                <div class="spec-row">
                    <span class="spec-label">尺寸:</span>
                    <span class="spec-value">${fan.size ? fan.size + ' mm' : '未知'}</span>
                </div>
            </div>
            ${fan.description ? `
                <div class="fan-description">
                    <div class="description-label">简介:</div>
                    <div class="description-text">${fan.description}</div>
                </div>
            ` : ''}
            <div class="fan-price">
                <div class="price-label">价格</div>
                <div class="price-value">${fan.price || '未知'}</div>
            </div>
        `;

        return card;
    }

    // 显示风扇详情模态框
    function showFanDetails(fan) {
        modalTitle.textContent = fan.name;
        
        modalBody.innerHTML = `
            <table class="detail-table">
                <tr>
                    <td class="detail-label">风扇型号:</td>
                    <td class="detail-value">${fan.name}</td>
                </tr>
                <tr>
                    <td class="detail-label">品牌:</td>
                    <td class="detail-value">${fan.brand || '未知'}</td>
                </tr>
                <tr>
                    <td class="detail-label">厚度:</td>
                    <td class="detail-value">${fan.thickness ? fan.thickness + ' mm' : '未知'}</td>
                </tr>
                <tr>
                    <td class="detail-label">轴承类型:</td>
                    <td class="detail-value">${fan.bearing || '未知'}</td>
                </tr>
                <tr>
                    <td class="detail-label">尺寸:</td>
                    <td class="detail-value">${fan.size ? fan.size + ' mm' : '未知'}</td>
                </tr>
                <tr>
                    <td class="detail-label">价格:</td>
                    <td class="detail-value">${fan.price || '未知'}</td>
                </tr>
            </table>
            ${fan.description ? `
                <div class="detail-description">
                    <div class="detail-description-title">产品简介:</div>
                    <div>${fan.description}</div>
                </div>
            ` : ''}
        `;

        modal.style.display = 'block';
    }

    // 关闭模态框
    modalClose.onclick = () => {
        modal.style.display = 'none';
    };

    window.onclick = (e) => {
        if (e.target === modal) {
            modal.style.display = 'none';
        }
    };

    // ESC键关闭模态框
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal.style.display === 'block') {
            modal.style.display = 'none';
        }
    });
});
