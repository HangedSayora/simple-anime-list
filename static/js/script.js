let animeList = [];
let currentPage = 1;
let animeToDelete = null;
let seasonAnime = null;
let animeToChangeURL = null;
let parent_id_v = 0;

// Main functions
async function fetchAnimeList() {
  seasonAnime = null;
   parent_id_v = 0;
  const searchQuery = document.getElementById('anime-title-search').value.toLowerCase();
  const statusFilter = document.getElementById('status-filter').value;

  const res = await fetch(`/api/anime-list?page=${currentPage}&search=${searchQuery}&status=${statusFilter}`);
  const data = await res.json();

  const animeList = data.anime_list;
  const totalPages = data.total_pages;
  const container = document.getElementById('anime-list');
  container.innerHTML = '';

  animeList.forEach(anime => {
    const el = document.createElement('div');
    el.className = 'anime';
    el.innerHTML = generateAnimeHTML(anime, false);
    container.appendChild(el);
  });

  updatePaginationControls(currentPage, totalPages);
}




function generateAnimeHTML(anime, hideButtons = false, isSeason = false) {
  return `
    <div class="anime-left">
      <img src="${anime.preview_url}" class="anime-img" height="230" alt="preview">
      <label class="anime-con" style="margin-top: 10px;">
        <select onchange="changeStatus('${anime.original_name}', this.value)">
          <option value="буду смотреть" ${anime.user_status === 'буду смотреть' ? 'selected' : ''}>Буду смотреть</option>
          <option value="смотрю" ${anime.user_status === 'смотрю' ? 'selected' : ''}>Смотрю</option>
          <option value="просмотрено" ${anime.user_status === 'просмотрено' ? 'selected' : ''}>Просмотрено</option>
          <option value="любимое" ${anime.user_status === 'любимое' ? 'selected' : ''}>Любимое</option>
          <option value="брошено" ${anime.user_status === 'брошено' ? 'selected' : ''}>Брошено</option>
        </select>
      </label>
    </div>
    <div class="anime-right">
      <strong class="anime-title">${anime.russian_name}</strong>
      <p class="anime-title2" style="color: #888;">(${anime.original_name})</p>
      <div class="anime-details">
        <p><strong>Эпизоды:</strong> ${anime.episodes}</p>
        <p><strong>Рейтинг:</strong> ${anime.rating}</p>
        <p><strong>Статус:</strong> ${anime.status}</p>
        <p><strong>${anime.start_date_label}</strong>${anime.start_date}</p>
        <p><strong>Вышел: </strong>${anime.last_date}</p>
      </div>
      <div class="anime-buttons">
        <div class="left-buttons">
          <button onclick="window.open('${anime.anime_url}', '_blank')">Смотреть</button>
          ${!isSeason && !hideButtons ? `<button onclick="showAllSeasons('${anime.original_name}', '${anime.id}')">Все сезоны</button>` : ''}
          ${isSeason ? `<button onclick="fetchAnimeList()">Весь список</button>` : ''}
        </div>
        <div class="right-buttons">
          <div class="move-buttons">
            ${!isSeason && !hideButtons ? `<button onclick="moveAnime('${anime.id}', 'up')"><img src="/static/icons/up_arrow.png" width="16" height="16" alt="move_up_anime" /></button>` : ''}
            ${!isSeason && !hideButtons ? `<button onclick="moveAnime('${anime.id}', 'down')"><img src="/static/icons/down_arrow.png" width="16" height="16" alt="move_down_anime" /></button>` : ''}
            ${isSeason && !hideButtons ? `<button onclick="moveSeason('${anime.id}', 'up', '${parent_id_v}')"><img src="/static/icons/up_arrow.png" width="16" height="16" alt="move_up_season" /></button>` : ''}
            ${isSeason && !hideButtons ? `<button onclick="moveSeason('${anime.id}', 'down', '${parent_id_v}')"><img src="/static/icons/down_arrow.png" width="16" height="16" alt="move_down_season" /></button>` : ''}
          </div>
          ${!isSeason && !hideButtons ? `<button onclick="showSeasonForm('${anime.russian_name}', '${anime.original_name}')">Добавить сезон</button>` : ''}
          <button onclick="showChangeForm('${anime.russian_name}', '${anime.original_name}')">Изменить</button>
          <button onclick="updateAnime('${anime.original_name}')">Обновить</button>
          <button onclick="showDeleteForm('${anime.original_name}', '${anime.russian_name}')">Удалить</button>
        </div>
      </div>
    </div>
  `;
}




async function fetchAnimeInfo(name) {
  const res = await fetch(`https://shikimori.one/api/animes?search=${encodeURIComponent(name)}`);
  const data = await res.json();
  return data.length ? data[0] : null;
}




async function loadAllAnimePages() {
  let page = 1;
  let allAnime = [];
  let totalPages = 1;

  do {
    const res = await fetch(`/api/anime-list?page=${page}`);
    const data = await res.json();
    if (Array.isArray(data.anime_list)) {
      allAnime.push(...data.anime_list);
    }
    totalPages = data.total_pages || 1;
    page++;
  } while (page <= totalPages);

  return allAnime;
}
//------------------------------------------------------------------------------------------





// Add functions
async function addAnime() {
  const title = document.getElementById('anime-title').value;
  const url = document.getElementById('anime-url').value;
  if (!title || !url) return alert('Заполните оба поля');
  await fetch('/api/anime', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, url })
  });
  document.getElementById('add-form').style.display = 'none';
  fetchAnimeList();
}




async function addSeason() {
  const title = document.getElementById('season-title').value;
  const url = document.getElementById('season-url').value;
  const form = document.getElementById('season-form');
  const parentName = form.dataset.parent;

  if (!title || !url) return alert('Заполните оба поля');

  await fetch(`/api/anime/${encodeURIComponent(parentName)}/add_season`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, url })
  });

  form.style.display = 'none';
  fetchAnimeList();
}
//------------------------------------------------------------------------------------------





// Change fuctions
async function changeStatus(name, newStatus) {
  await fetch(`/api/anime/${encodeURIComponent(name)}/status`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_status: newStatus })
  });
}




async function changeUrl(name) {
  const newUrl = document.getElementById('change-url').value;

  await fetch(`/api/anime/${encodeURIComponent(name)}/url`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ anime_url: newUrl })
  });

  updateAnimeListOverall();

  animeToChangeURL = null;
  document.getElementById('change-form').style.display = 'none';
}




function changePage(page) {
  currentPage = page;
  updateAnimeListOverall();
}
//------------------------------------------------------------------------------------------





// Confirm functions
async function confirmDelete() {
  if (animeToDelete) {
    await fetch(`/api/anime/${encodeURIComponent(animeToDelete)}`, { method: 'DELETE' });
    updateAnimeListOverall();
    animeToDelete = null;
    document.getElementById('del-form').style.display = 'none';
  }
}




function confirmChangeURL() {
  if (animeToChangeURL) {
    changeUrl(animeToChangeURL);
  }
}
//------------------------------------------------------------------------------------------





// Updates functions
async function updateAnimeListOverall() {
  if (seasonAnime) {
    await showAllSeasons(seasonAnime, parent_id_v);
  } else {
    await fetchAnimeList();
  }
}




function updatePaginationControls(currentPage, totalPages) {
  const paginationPrev = document.getElementById('pagination-prev');
  const paginationPage = document.getElementById('pagination-page');
  const paginationNext = document.getElementById('pagination-next');
  paginationPrev.innerHTML = '';
  paginationPage.innerHTML = '';
  paginationNext.innerHTML = '';

  const pageRange = 5;
  let startPage = Math.max(1, currentPage - Math.floor(pageRange / 2));
  let endPage = Math.min(totalPages, currentPage + Math.floor(pageRange / 2));

  if (endPage - startPage + 1 < pageRange) {
    if (currentPage < Math.floor(pageRange / 2) + 1) {
      endPage = Math.min(totalPages, pageRange);
    } else if (currentPage > totalPages - Math.floor(pageRange / 2)) {
      startPage = Math.max(1, totalPages - pageRange + 1);
    }
  }

  if (currentPage > 1) {
    const prevButton = document.createElement('button');
    prevButton.textContent = 'Назад';
    prevButton.onclick = () => changePage(currentPage - 1);
    paginationPrev.appendChild(prevButton);
  }

  for (let i = startPage; i <= endPage; i++) {
    const pageButton = document.createElement('button');
    pageButton.textContent = i;
    pageButton.classList.toggle('active', i === currentPage);
    pageButton.onclick = () => changePage(i);
    paginationPage.appendChild(pageButton);
  }

  if (currentPage < totalPages) {
    const nextButton = document.createElement('button');
    nextButton.textContent = 'Вперед';
    nextButton.onclick = () => changePage(currentPage + 1);
    paginationNext.appendChild(nextButton);
  }
}




async function updateAnime(name) {
  if (!animeList.length || true) {
    animeList = await loadAllAnimePages();
  }

  if (!Array.isArray(animeList)) {
    alert("Ошибка: данные не в формате массива!");
    return;
  }

  let foundAnime = null;
  let parentAnime = null;

  for (const anime of animeList) {
    if (anime.original_name === name || anime.russian_name === name) {
      foundAnime = anime;
      break;
    }

    if (Array.isArray(anime.seasons)) {
      for (const season of anime.seasons) {
        if (season.original_name === name || season.russian_name === name) {
          foundAnime = season;
          parentAnime = anime;
          break;
        }
      }
    }

    if (foundAnime) break;
  }

  if (!foundAnime) {
    return alert("Аниме не найдено");
  }

  const info = await fetchAnimeInfo(foundAnime.original_name);
  if (info) {
    const updated = {
      ...info,
      anime_url: foundAnime.anime_url || foundAnime.url || "",
      user_status: foundAnime.user_status || "буду смотреть"
    };

    console.log("Updated anime:", updated);

    const res = await fetch(`/api/anime/${encodeURIComponent(foundAnime.original_name)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updated)
    });

    const responseBody = await res.text();
    console.log("Response status:", res.status);
    console.log("Response body:", responseBody);

    if (res.ok) {
      updateAnimeListOverall();
    } else {
      alert("Ошибка при обновлении.");
    }
  } else {
    alert("Не удалось получить данные с Shikimori.");
  }
}
//------------------------------------------------------------------------------------------





// Move Anime in main list
function moveAnime(id, direction) {
  fetch(`/api/anime/${encodeURIComponent(id)}/move?direction=${direction}`, {
    method: 'PUT'
  })
  .then(response => {
    if (!response.ok) {
      throw new Error('Move failed');
    }
    return response.text();
  })
  .then(() => {
    updateAnimeListOverall();
  })
  .catch(err => {
    console.error(err);
  });
}

function moveSeason(id, direction, parent_id) {
  fetch(`/api/season/${encodeURIComponent(id)}/move?direction=${direction}&parent_id=${parent_id}`, {
    method: 'PUT'
  })
  .then(response => {
    if (!response.ok) {
      throw new Error('Move failed');
    }
    return response.text();
  })
  .then(() => {
    updateAnimeListOverall();
  })
  .catch(err => {
    console.error(err);
  });
}
//------------------------------------------------------------------------------------------





// Shows functions
async function showAllSeasons(animeName, parent_id) {
  parent_id_v = parent_id;
  updatePaginationControls(0, 0);
  const searchQuery = document.getElementById('anime-title-search').value.toLowerCase();
  const statusFilter = document.getElementById('status-filter').value;
  seasonAnime = animeName;
  const res = await fetch(`/api/anime-list?search_season=${searchQuery}&status_season=${statusFilter}&full=false`);
  const data = await res.json();
  const container = document.getElementById('anime-list');
  container.innerHTML = '';

  const anime = data.anime_list.find(a =>
    a.original_name === animeName || a.russian_name === animeName
  );
  if (!anime) return;

  if (anime.seasons?.length) {
    anime.seasons.forEach(season => {
      const seasonEl = document.createElement('div');
      seasonEl.className = 'anime season';
      seasonEl.innerHTML = generateAnimeHTML(season, false, true);
      container.appendChild(seasonEl);
    });
  }
}




function showDeleteForm(nameEnglish, nameRussian) {
  animeToDelete = nameEnglish;
  const form = document.getElementById('del-form');
  document.getElementById('del-form').style.display = 'flex';

  form.querySelector('h2').textContent = `Вы уверены, что хотите удалить "${nameRussian}"`;
}




function showAddForm() {
  document.getElementById('add-form').style.display = 'flex';
  document.getElementById('anime-title').value = '';
  document.getElementById('anime-url').value = '';
}




function showSeasonForm(nameRussian, nameEnglish) {
  const form = document.getElementById('season-form');
  document.getElementById('season-form').style.display = 'flex';

  form.dataset.parent = nameEnglish;
  form.querySelector('h2').textContent = `Добавление сезона к "${nameRussian}"`;
  document.getElementById('season-title').value = '';
  document.getElementById('season-url').value = '';
}




function showChangeForm(nameRussian, nameEnglish) {
  animeToChangeURL = nameEnglish;
  const form = document.getElementById('change-form');
  document.getElementById('change-form').style.display = 'flex';

  form.dataset.parent = nameEnglish;
  form.querySelector('h2').textContent = `Изменение URL "${nameRussian}"`;
  document.getElementById('change-url').value = '';
}
//------------------------------------------------------------------------------------------





// Close all's modal window on click anyway 
function cancelForm() {
  document.getElementById('add-form').style.display = 'none';
  document.getElementById('del-form').style.display = 'none';
  document.getElementById('season-form').style.display = 'none';
  document.getElementById('change-form').style.display = 'none';
}
//------------------------------------------------------------------------------------------





// Others functions
window.onload = function() {
  document.getElementById('add-form').style.display = 'none';
  document.getElementById('del-form').style.display = 'none';
  document.getElementById('season-form').style.display = 'none';
  document.getElementById('change-form').style.display = 'none';
  document.getElementById('anime-title-search').addEventListener('input', updateAnimeListOverall);
};




window.addEventListener('click', function(event) {
  const addForm = document.getElementById('add-form');
  const delForm = document.getElementById('del-form');
  const seasonForm = document.getElementById('season-form');
  const changeForm = document.getElementById('change-form');

  if (event.target === addForm || event.target === delForm || event.target === seasonForm || event.target === changeForm) {
    cancelForm();
  }
});




document.getElementById('anime-title-search').addEventListener('input', () => {
  currentPage = 1;
  updateAnimeListOverall();
});




document.getElementById('status-filter').addEventListener('change', () => {
  currentPage = 1;
  updateAnimeListOverall();
});




const placeholders = [
  'Введите название аниме..',
  'Введите название аниме.',
  'Введите название аниме..',
  'Введите название аниме...'
];




let index = 0;
setInterval(() => {
  const input = document.getElementById('anime-title-search');
  input.placeholder = placeholders[index];
  index = (index + 1) % placeholders.length;
}, 500);
//------------------------------------------------------------------------------------------





fetchAnimeList();