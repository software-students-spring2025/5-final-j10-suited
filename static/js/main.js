document.addEventListener("DOMContentLoaded", async(event) => {
    console.log("DOM fully loaded and parsed");

    let current_sort = 'oldest'
    let current_search_text = ''

    const search_bar = document.querySelector('.group-search')
    search_bar.addEventListener('input', (event) => {
        search_text = event.target.value.toLowerCase()
        current_search_text = search_text
        display_groups(current_search_text, current_sort)
    })

    const sort_options = document.querySelector('.sort-options')
    const menu = document.querySelector('.menu')
    const click_off = document.querySelector('.click-off')


    click_off.addEventListener('click', (event) => {
        menu.style.display = "none";
        menu.style.opacity = 0;
        click_off.style.display = "none";
    })
    sort_options.addEventListener('click', (event) => {
        menu.style.display = 'block';
        menu.style.opacity = 1;
        click_off.style.display = 'block';
    })

    document.querySelectorAll('.menu li').forEach(li => {
        li.addEventListener('click', () => {
            const sort = li.getAttribute('data-sort')
            current_sort = sort
            display_groups(current_search_text, current_sort)
        });
    });

});

async function display_groups(text, sort='oldest') {
    const response = await fetch(`get_all_groups?sort=${sort}`)
    if (!response.ok){
        console.error('Failed to fetch groups')
        return
    }

    const groups_data = await response.json()
    const group_browser = document.querySelector('.group-browser')
    group_browser.innerHTML = '';

    for (const group_data of groups_data) {
        if (group_data['name'].toLowerCase().includes(text.toLowerCase())) {
            create_group_div(group_data);
        }
    }
}

function create_group_div(data) {
    const group_browser = document.querySelector('.group-browser')
    const group = document.createElement('a')
    const b = document.createElement('b')

    const group_id = data['_id']
    const group_name = data['name']
    const group_members = data['members']
    const num_members = group_members.length

    group.className = 'group'
    group.href = `/group_detail/${group_id}`;
    b.textContent = group_name;

    const members = document.createElement('span')
    
    if (num_members == 1) {
        members.textContent = num_members + ' Member'
    } else {
        members.textContent = num_members + ' Members'
    }

    group.appendChild(b);
    group.appendChild(members);
    group_browser.appendChild(group);
}