let animeList = [];
let currentPage = 1;
let animeToDelete = null;

async function fetchAnimeList() {
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
    el.innerHTML = `
      <div class="anime-left">
        <img src="${anime.image_original}" class="anime-img" height="230" alt="preview">
        <label class="anime-con" style="margin-top: 10px;">
          <select onchange="changeStatus('${anime.name}', this.value)">
            <option value="буду смотреть" ${anime.user_status === 'буду смотреть' ? 'selected' : ''}>Буду смотреть</option>
            <option value="смотрю" ${anime.user_status === 'смотрю' ? 'selected' : ''}>Смотрю</option>
            <option value="просмотрено" ${anime.user_status === 'просмотрено' ? 'selected' : ''}>Просмотрено</option>
            <option value="любимое" ${anime.user_status === 'любимое' ? 'selected' : ''}>Любимое</option>
            <option value="брошено" ${anime.user_status === 'брошено' ? 'selected' : ''}>Брошено</option>
          </select>
        </label>
      </div>
      <div class="anime-right">
        <strong class="anime-title">${anime.russian}</strong>
        <p class="anime-title2" style="color: #888;">(${anime.name})</p>
        <div class="anime-details">
          <p><strong>Эпизоды:</strong> ${anime.episodes}</p>
          <p><strong>Рейтинг:</strong> ${anime.score}</p>
          <p><strong>Статус:</strong> ${anime.status}</p>
          <p><strong>${anime.aired_label}</strong>${anime.aired_on}</p>
          <p><strong>Вышел: </strong>${anime.released_on}</p>
        </div>
        <div class="anime-buttons">
          <div class="left-button">
            <button onclick="window.open('${anime.url}', '_blank')">Смотреть</button>
          </div>
          <div class="right-buttons">
            <div class="move-buttons">
              <button onclick="moveAnime('${anime.name}', 'up')">↑</button>
              <button onclick="moveAnime('${anime.name}', 'down')">↓</button>
            </div>
            <button onclick="updateAnime('${anime.name}')">Обновить</button>
            <button onclick="showDeleteModal('${anime.name}', '${anime.russian}')">Удалить</button>
          </div>

        </div>
      </div>
    `;
    container.appendChild(el);
  });

  updatePaginationControls(currentPage, totalPages);
}

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

    async function fetchAnimeInfo(name) {
      const res = await fetch(`https://shikimori.one/api/animes?search=${encodeURIComponent(name)}`);
      const data = await res.json();
      return data.length ? data[0] : null;
    }

    async function updateAnime(name) {
      if (!animeList.length) {
        const res = await fetch('/api/anime-list');
        animeList = await res.json();
      }

      const anime = animeList.find(a => a.name === name);
      if (!anime) return alert("Аниме не найдено");

      const info = await fetchAnimeInfo(anime.name);
      if (info) {
        const updated = { ...info, url: anime.url, user_status: anime.user_status };
        console.log("Updated anime:", updated);

        const res = await fetch(`/api/anime/${encodeURIComponent(anime.name)}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(updated)
        });

        const responseBody = await res.text();
        console.log("Response status:", res.status);
        console.log("Response body:", responseBody);

        if (res.ok) {
          fetchAnimeList();
        } else {
          alert("Ошибка при обновлении.");
        }
      } else {
        alert("Не удалось получить данные с Shikimori.");
      }
    }

    async function changeStatus(name, newStatus) {
      await fetch(`/api/anime/${encodeURIComponent(name)}/status`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_status: newStatus })
      });
      fetchAnimeList();
    }

    window.onload = function() {
      document.getElementById('add-form').style.display = 'none';
      document.getElementById('anime-title-search').addEventListener('input', fetchAnimeList);
      document.getElementById('del-form').style.display = 'none';
    };

function showAddForm() {
      document.getElementById('add-form').style.display = 'flex';
    }

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

function changePage(page) {
  currentPage = page;
  fetchAnimeList();
}

document.getElementById('anime-title-search').addEventListener('input', () => {
  currentPage = 1;
  fetchAnimeList();
});

document.getElementById('status-filter').addEventListener('change', () => {
  currentPage = 1;
  fetchAnimeList();
});

function showDeleteModal(name, russian) {
  animeToDelete = name;
  document.getElementById('del-form').style.display = 'flex';

  const modalMessage = document.getElementById('modalMessage');
  modalMessage.textContent = `Вы уверены, что хотите удалить "${russian}"?`;
}

function closeDeleteModal() {
  animeToDelete = null;
  document.getElementById('del-form').style.display = 'none';
}

document.getElementById('confirmDelete').addEventListener('click', async () => {
  if (animeToDelete) {
    await fetch(`/api/anime/${encodeURIComponent(animeToDelete)}`, { method: 'DELETE' });
    fetchAnimeList();
    closeDeleteModal();
  }
});

function cancelForm() {
  document.getElementById('add-form').style.display = 'none';
  document.getElementById('del-form').style.display = 'none';
}


window.addEventListener('click', function(event) {
  const addForm = document.getElementById('add-form');
  const delForm = document.getElementById('del-form');

  if (event.target === addForm || event.target === delForm) {
    cancelForm();
  }
});

function moveAnime(name, direction) {
  fetch(`/api/anime/${encodeURIComponent(name)}/move?direction=${direction}`, {
    method: 'PUT'
  })
  .then(response => {
    if (!response.ok) {
      throw new Error('Move failed');
    }
    return response.text();
  })
  .then(() => {
    fetchAnimeList();
  })
  .catch(err => {
    console.error(err);
  });
}


fetchAnimeList();
