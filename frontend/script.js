async function searchBooks(){

    let query=
        document.getElementById("query").value;

    let author=
        document.getElementById("author").value;

    let rating=
        document.getElementById("rating").value;

    let tag=
        document.getElementById("tag").value;


    let url=
`http://localhost:8000/books/search?q=${query}&author=${author}&min_rating=${rating}&tag=${tag}`;


    let response=
        await fetch(url);

    let books=
        await response.json();

    let resultsDiv=
        document.getElementById("results");

    resultsDiv.innerHTML="";


    books.forEach(book=>{

        resultsDiv.innerHTML +=
        `
        <div>

            <h3>${book.title}</h3>

            <p>Rating: ${book.rating}</p>

        </div>

        <hr>
        `;

    });

}